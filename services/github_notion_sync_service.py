from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config.settings import (
    GITHUB_DEFAULT_REPO,
    GITHUB_SYNC_DEFAULT_HOURS,
    GITHUB_SYNC_STATE_FILE,
    NOTION_UPDATES_PAGE_ID,
)
from services.integration_settings_service import get_integration_setting
from services.github_service import (
    GitHubServiceError,
    fetch_recent_commits,
    fetch_recent_pull_requests,
    now_utc_iso,
)
from services.notion_service import NotionServiceError, append_markdown_like_entry, read_page_text


def sync_project_updates_to_notion(
    *,
    repo: str | None = None,
    page_id: str | None = None,
    hours: int | None = None,
) -> str:
    resolved_repo = _resolve_repo(repo)
    if not resolved_repo:
        return "Не указан репозиторий. Задай GITHUB_DEFAULT_REPO=owner/repo или скажи: синхронизируй github owner/repo в notion."

    resolved_page = _resolve_page(page_id)
    if not resolved_page:
        return "Не указан Notion page id. Задай NOTION_UPDATES_PAGE_ID."

    since_iso = _resolve_since_iso(resolved_repo, hours=hours)
    try:
        commits = fetch_recent_commits(resolved_repo, since_iso=since_iso, limit=12)
        pull_requests = fetch_recent_pull_requests(resolved_repo, since_iso=since_iso, limit=8)
    except GitHubServiceError as exc:
        return f"Не удалось получить обновления из GitHub: {exc}"
    except Exception as exc:
        return f"Ошибка при чтении GitHub: {type(exc).__name__}: {exc}"

    if not commits and not pull_requests:
        _update_sync_state(resolved_repo, now_utc_iso())
        return "Новых изменений в GitHub с последней синхронизации не нашла."

    title = f"GitHub update: {resolved_repo} ({_display_utc_now()})"
    lines = _build_update_lines(commits, pull_requests)
    try:
        append_markdown_like_entry(resolved_page, title, lines)
    except NotionServiceError as exc:
        return f"Не удалось записать обновление в Notion: {exc}"
    except Exception as exc:
        return f"Ошибка при записи в Notion: {type(exc).__name__}: {exc}"

    _update_sync_state(resolved_repo, now_utc_iso())
    return (
        f"Синхронизировала GitHub в Notion: {len(commits)} commits, "
        f"{len(pull_requests)} PR."
    )


def read_notion_updates_page(*, page_id: str | None = None, limit: int = 10) -> str:
    resolved_page = _resolve_page(page_id)
    if not resolved_page:
        return "Не указан Notion page id. Задай NOTION_UPDATES_PAGE_ID."
    try:
        lines = read_page_text(resolved_page, limit=limit)
    except NotionServiceError as exc:
        return f"Не удалось прочитать Notion: {exc}"
    except Exception as exc:
        return f"Ошибка при чтении Notion: {type(exc).__name__}: {exc}"
    if not lines:
        return "Страница Notion пока пустая или в первых блоках нет текста."
    preview = "; ".join(lines[:5])
    return f"В Notion сейчас: {preview}"


def append_note_to_notion(text: str, *, page_id: str | None = None) -> str:
    normalized = " ".join(str(text).strip().split())
    if not normalized:
        return "Скажи, какой текст добавить в Notion."
    resolved_page = _resolve_page(page_id)
    if not resolved_page:
        return "Не указан Notion page id. Задай NOTION_UPDATES_PAGE_ID."
    try:
        append_markdown_like_entry(
            resolved_page,
            f"Vasya note ({_display_utc_now()})",
            [normalized],
        )
    except NotionServiceError as exc:
        return f"Не удалось записать заметку в Notion: {exc}"
    except Exception as exc:
        return f"Ошибка при записи в Notion: {type(exc).__name__}: {exc}"
    return "Добавила запись в Notion."


def _resolve_repo(repo: str | None) -> str:
    candidate = " ".join(str(repo or "").strip().split())
    if candidate:
        return candidate
    configured = get_integration_setting("github_default_repo")
    if configured:
        return configured
    return GITHUB_DEFAULT_REPO


def _resolve_page(page_id: str | None) -> str:
    candidate = " ".join(str(page_id or "").strip().split())
    if candidate:
        return candidate
    configured = get_integration_setting("notion_updates_page_id")
    if configured:
        return configured
    return NOTION_UPDATES_PAGE_ID


def _resolve_since_iso(repo: str, *, hours: int | None) -> str:
    state = _load_sync_state()
    by_repo = state.get("repos", {}) if isinstance(state.get("repos", {}), dict) else {}
    stored = by_repo.get(repo)
    if isinstance(stored, str) and stored.strip():
        return stored

    fallback_hours = max(1, int(hours if isinstance(hours, int) else GITHUB_SYNC_DEFAULT_HOURS))
    return (datetime.now(timezone.utc) - timedelta(hours=fallback_hours)).isoformat()


def _sync_state_path() -> Path:
    return Path(GITHUB_SYNC_STATE_FILE)


def _load_sync_state() -> dict:
    path = _sync_state_path()
    if not path.exists():
        return {"repos": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"repos": {}}
    if not isinstance(payload, dict):
        return {"repos": {}}
    repos = payload.get("repos")
    if not isinstance(repos, dict):
        return {"repos": {}}
    return {"repos": repos}


def _update_sync_state(repo: str, timestamp_iso: str) -> None:
    state = _load_sync_state()
    repos = state.setdefault("repos", {})
    if not isinstance(repos, dict):
        repos = {}
        state["repos"] = repos
    repos[repo] = timestamp_iso

    path = _sync_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _display_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _build_update_lines(commits: list[dict], pull_requests: list[dict]) -> list[str]:
    lines: list[str] = []
    for pr in pull_requests:
        number = pr.get("number", 0)
        title = pr.get("title", "")
        state = pr.get("state", "")
        url = pr.get("url", "")
        lines.append(f"PR #{number} ({state}): {title} {url}".strip())
    for commit in commits:
        sha = commit.get("sha", "")
        message = commit.get("message", "")
        author = commit.get("author", "")
        url = commit.get("url", "")
        lines.append(f"commit {sha} by {author}: {message} {url}".strip())
    return lines
