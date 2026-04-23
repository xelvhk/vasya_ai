from __future__ import annotations

from config.settings import GITHUB_DEFAULT_REPO
from services.github_service import (
    GitHubServiceError,
    fetch_repository_metadata,
    fetch_repository_readme,
)
from services.integration_settings_service import get_integration_setting
from services.obsidian_service import upsert_obsidian_note, upsert_project_note_from_readme


def update_obsidian_note(*, title: str, content: str, mode: str = "append") -> str:
    normalized_title = " ".join(str(title or "").strip().split())
    normalized_content = str(content or "").strip()
    if not normalized_content:
        return "Не указан текст для заметки в Obsidian."

    result = upsert_obsidian_note(
        title=normalized_title or "Vasya Note",
        content=normalized_content,
        mode="replace" if mode == "replace" else "append",
    )
    if not result.get("ok"):
        return str(result.get("error") or "Не удалось обновить заметку в Obsidian.")
    path = str(result.get("path", ""))
    if mode == "replace":
        return f"Готово. Обновила заметку в Obsidian: {path}."
    return f"Готово. Добавила в заметку Obsidian: {path}."


def sync_github_project_to_obsidian(*, repo: str | None = None) -> str:
    resolved_repo = _resolve_repo(repo)
    if not resolved_repo:
        return (
            "Не указан GitHub репозиторий. "
            "Скажи: добавь проект github owner/repo в обсидиан."
        )
    try:
        metadata = fetch_repository_metadata(resolved_repo)
        readme = fetch_repository_readme(resolved_repo)
    except GitHubServiceError as exc:
        return f"Не удалось получить данные проекта из GitHub: {exc}"
    except Exception as exc:
        return f"Ошибка при чтении GitHub: {type(exc).__name__}: {exc}"

    result = upsert_project_note_from_readme(
        repo=str(metadata.get("full_name") or resolved_repo),
        readme_markdown=str(readme.get("text") or ""),
        repo_description=str(metadata.get("description") or ""),
        repo_url=str(metadata.get("html_url") or ""),
        default_branch=str(metadata.get("default_branch") or "main"),
    )
    if not result.get("ok"):
        return str(result.get("error") or "Не удалось записать проект в Obsidian.")
    return (
        "Синхронизировала проект GitHub в Obsidian. "
        f"Файл: {result.get('path', '')}."
    )


def _resolve_repo(repo: str | None) -> str:
    candidate = " ".join(str(repo or "").strip().split())
    if candidate:
        return candidate
    configured = get_integration_setting("github_default_repo")
    if configured:
        return configured
    return GITHUB_DEFAULT_REPO
