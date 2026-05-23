from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from config.settings import GITHUB_DEFAULT_REPO, NOTION_UPDATES_PAGE_ID
from services.github_service import (
    fetch_recent_commits,
    fetch_recent_pull_requests,
    now_utc_iso,
)
from services.integration_settings_service import get_integration_setting
from services.memory_center_service import MemoryCenterService, MemorySyncPlanner
from services.notion_service import read_page_text
from services.obsidian_knowledge_service import build_vault_index
from services.obsidian_service import resolve_obsidian_vault_path


def sync_memory_source(
    source: str,
    *,
    force: bool = False,
    repo: str | None = None,
    page_id: str | None = None,
) -> dict:
    normalized = str(source or "").strip().lower()
    if normalized == "github":
        return sync_github_to_memory(repo=repo, force=force)
    if normalized == "notion":
        return sync_notion_to_memory(page_id=page_id, force=force)
    if normalized == "obsidian":
        return sync_obsidian_to_memory(force=force)
    if normalized == "all":
        results = [
            sync_github_to_memory(repo=repo, force=force),
            sync_notion_to_memory(page_id=page_id, force=force),
            sync_obsidian_to_memory(force=force),
        ]
        successful = [
            item for item in results if item.get("ok") and not item.get("skipped")
        ]
        skipped = [item for item in results if item.get("skipped")]
        errors = [
            item for item in results if not item.get("ok") and not item.get("skipped")
        ]
        return {
            "ok": bool(successful or skipped) and len(errors) < len(results),
            "source": "all",
            "results": results,
            "ingested": sum(int(item.get("ingested", 0)) for item in results),
            "successful_sources": [str(item.get("source")) for item in successful],
            "skipped_sources": [str(item.get("source")) for item in skipped],
            "errors": errors,
        }
    return {"ok": False, "source": normalized, "error": "Unsupported memory source."}


def sync_github_to_memory(*, repo: str | None = None, force: bool = False) -> dict:
    resolved_repo = _resolve_repo(repo)
    if not resolved_repo:
        return {"ok": False, "source": "github", "error": "GitHub repo is not configured."}

    source_key = f"github_{_source_fragment(resolved_repo)}"
    planner = MemorySyncPlanner()
    decision = planner.should_sync("github", resolved_repo)
    if not force and not decision.due:
        return {
            "ok": True,
            "skipped": True,
            "source": "github",
            "reason": "not_due",
            "next_sync_at_ts": decision.next_sync_at_ts,
        }

    since_iso = decision.cursor or _fallback_since_iso(hours=24)
    commits = fetch_recent_commits(resolved_repo, since_iso=since_iso, limit=12)
    pull_requests = fetch_recent_pull_requests(resolved_repo, since_iso=since_iso, limit=8)

    memory = MemoryCenterService()
    ingested = 0
    for pr in pull_requests:
        number = int(pr.get("number", 0))
        title = str(pr.get("title", "")).strip() or f"PR #{number}"
        content = "\n".join(
            [
                f"Repository: {resolved_repo}",
                f"Pull request: #{number}",
                f"State: {pr.get('state', 'unknown')}",
                f"Updated: {pr.get('updated_at', '')}",
                f"URL: {pr.get('url', '')}",
            ]
        )
        memory.ingest_text(
            source_key=source_key,
            source_name=f"GitHub {resolved_repo}",
            source_kind="github",
            title=f"PR #{number}: {title}",
            content=content,
            external_id=f"pr:{number}",
            url=str(pr.get("url", "")),
            tags=("github", "pull-request"),
        )
        ingested += 1

    for commit in commits:
        sha = str(commit.get("sha", "")).strip()
        message = str(commit.get("message", "")).strip() or "Commit"
        content = "\n".join(
            [
                f"Repository: {resolved_repo}",
                f"Commit: {sha}",
                f"Message: {message}",
                f"Author: {commit.get('author', 'unknown')}",
                f"Date: {commit.get('date', '')}",
                f"URL: {commit.get('url', '')}",
            ]
        )
        memory.ingest_text(
            source_key=source_key,
            source_name=f"GitHub {resolved_repo}",
            source_kind="github",
            title=f"commit {sha}: {message}",
            content=content,
            external_id=f"commit:{sha}",
            url=str(commit.get("url", "")),
            tags=("github", "commit"),
        )
        ingested += 1

    cursor = now_utc_iso()
    planner.record_success(
        "github",
        resolved_repo,
        cursor=cursor,
        items_count=ingested,
    )
    return {
        "ok": True,
        "source": "github",
        "repo": resolved_repo,
        "ingested": ingested,
        "cursor": cursor,
    }


def sync_notion_to_memory(*, page_id: str | None = None, force: bool = False) -> dict:
    resolved_page = _resolve_page(page_id)
    if not resolved_page:
        return {"ok": False, "source": "notion", "error": "Notion page id is not configured."}

    planner = MemorySyncPlanner()
    decision = planner.should_sync("notion", resolved_page)
    if not force and not decision.due:
        return {
            "ok": True,
            "skipped": True,
            "source": "notion",
            "reason": "not_due",
            "next_sync_at_ts": decision.next_sync_at_ts,
        }

    lines = read_page_text(resolved_page, limit=50)
    content = "\n".join(f"- {line}" for line in lines) if lines else "No readable text blocks found."
    memory = MemoryCenterService()
    memory.ingest_text(
        source_key=f"notion_{_source_fragment(resolved_page)}",
        source_name="Notion updates page",
        source_kind="notion",
        title="Notion page snapshot",
        content=content,
        external_id="page-snapshot",
        tags=("notion", "snapshot"),
    )
    cursor = now_utc_iso()
    planner.record_success(
        "notion",
        resolved_page,
        cursor=cursor,
        items_count=1 if lines else 0,
    )
    return {
        "ok": True,
        "source": "notion",
        "page_id": resolved_page,
        "ingested": 1,
        "cursor": cursor,
    }


def sync_obsidian_to_memory(*, force: bool = False, limit: int = 80) -> dict:
    vault_path, error = resolve_obsidian_vault_path()
    if error or vault_path is None:
        return {"ok": False, "source": "obsidian", "error": error or "Obsidian vault not configured."}

    connection_id = str(vault_path)
    planner = MemorySyncPlanner()
    decision = planner.should_sync("obsidian", connection_id)
    if not force and not decision.due:
        return {
            "ok": True,
            "skipped": True,
            "source": "obsidian",
            "reason": "not_due",
            "next_sync_at_ts": decision.next_sync_at_ts,
        }

    index = build_vault_index(vault_path, limit=limit)
    if not index.get("ok"):
        return {"ok": False, "source": "obsidian", "error": index.get("error", "Vault index failed.")}

    memory = MemoryCenterService()
    ingested = 0
    for item in index.get("items", []):
        if not isinstance(item, dict):
            continue
        relpath = str(item.get("path", "")).strip()
        note_path = Path(relpath)
        if not note_path.is_absolute():
            note_path = Path(vault_path) / relpath
        if not note_path.exists() or not note_path.is_file():
            continue
        try:
            note_text = note_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        title = str(item.get("title") or note_path.stem)
        tags = tuple(str(tag) for tag in item.get("tags", []) if str(tag).strip())
        content = note_text.strip()
        if not content:
            continue
        memory.ingest_text(
            source_key="obsidian_vault",
            source_name="Obsidian vault",
            source_kind="obsidian",
            title=title,
            content=content[:12000],
            external_id=str(note_path.relative_to(vault_path)),
            tags=("obsidian",) + tags,
        )
        ingested += 1

    cursor = now_utc_iso()
    planner.record_success(
        "obsidian",
        connection_id,
        cursor=cursor,
        items_count=ingested,
    )
    return {
        "ok": True,
        "source": "obsidian",
        "vault_path": str(vault_path),
        "ingested": ingested,
        "cursor": cursor,
    }


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


def _fallback_since_iso(*, hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def _source_fragment(value: str) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace("/", "_")
        .replace(":", "_")
        .replace(" ", "_")
        .replace("-", "_")
    )
