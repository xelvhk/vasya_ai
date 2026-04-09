from __future__ import annotations

from datetime import datetime, timezone

import requests

from config.settings import GITHUB_API_BASE_URL, GITHUB_API_TOKEN
from services.integration_settings_service import get_integration_setting


class GitHubServiceError(Exception):
    pass


def fetch_recent_commits(repo: str, *, since_iso: str, limit: int = 10) -> list[dict]:
    repo_name = _normalize_repo(repo)
    if not repo_name:
        raise GitHubServiceError("Не указан GitHub-репозиторий в формате owner/repo.")

    response = requests.get(
        f"{GITHUB_API_BASE_URL}/repos/{repo_name}/commits",
        headers=_build_headers(),
        params={"since": since_iso, "per_page": max(1, min(limit, 30))},
        timeout=20,
    )
    if response.status_code >= 400:
        raise GitHubServiceError(_format_error("GitHub commits", response))
    payload = response.json()
    if not isinstance(payload, list):
        return []

    items: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        commit_block = item.get("commit", {})
        author_block = commit_block.get("author", {}) if isinstance(commit_block, dict) else {}
        message = str(commit_block.get("message", "")).strip().splitlines()[0]
        sha = str(item.get("sha", ""))[:7]
        html_url = str(item.get("html_url", ""))
        date_text = str(author_block.get("date", ""))
        items.append(
            {
                "sha": sha,
                "message": message or "Без сообщения",
                "author": str(author_block.get("name", "")).strip() or "unknown",
                "date": date_text,
                "url": html_url,
            }
        )
    return items


def fetch_recent_pull_requests(repo: str, *, since_iso: str, limit: int = 10) -> list[dict]:
    repo_name = _normalize_repo(repo)
    if not repo_name:
        raise GitHubServiceError("Не указан GitHub-репозиторий в формате owner/repo.")

    response = requests.get(
        f"{GITHUB_API_BASE_URL}/repos/{repo_name}/pulls",
        headers=_build_headers(),
        params={"state": "all", "sort": "updated", "direction": "desc", "per_page": max(1, min(limit, 30))},
        timeout=20,
    )
    if response.status_code >= 400:
        raise GitHubServiceError(_format_error("GitHub pull requests", response))
    payload = response.json()
    if not isinstance(payload, list):
        return []

    threshold = _safe_parse_iso(since_iso)
    items: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        updated_at = str(item.get("updated_at", ""))
        updated_dt = _safe_parse_iso(updated_at)
        if threshold and updated_dt and updated_dt < threshold:
            continue
        items.append(
            {
                "number": int(item.get("number", 0)),
                "title": str(item.get("title", "")).strip() or "Без названия",
                "state": str(item.get("state", "")).strip() or "unknown",
                "updated_at": updated_at,
                "url": str(item.get("html_url", "")),
            }
        )
        if len(items) >= limit:
            break
    return items


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_headers() -> dict[str, str]:
    token = get_integration_setting("github_api_token") or GITHUB_API_TOKEN
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "vasya-ai",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _normalize_repo(repo: str) -> str:
    normalized = " ".join(str(repo).strip().split())
    return normalized


def _safe_parse_iso(value: str) -> datetime | None:
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _format_error(label: str, response: requests.Response) -> str:
    try:
        payload = response.json()
        message = payload.get("message", "") if isinstance(payload, dict) else ""
    except ValueError:
        message = ""
    details = f": {message}" if message else ""
    return f"{label} API вернул {response.status_code}{details}"
