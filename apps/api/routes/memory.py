from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter

from apps.api.schemas import MemoryDigestRequest, MemorySyncRequest
from services.memory_center_service import (
    build_memory_daily_digest,
    get_memory_center_status,
    list_memory_daily_digests,
    list_recent_memory_center,
    search_memory_center,
)
from services.memory_sync_service import sync_memory_source


router = APIRouter(prefix="/v1/memory", tags=["memory"])


@router.get("/status")
def memory_status() -> dict:
    return get_memory_center_status()


@router.get("/search")
def memory_search(query: str, limit: int = 10) -> dict:
    safe_limit = min(50, max(1, int(limit)))
    return search_memory_center(query, limit=safe_limit)


@router.get("/recent")
def memory_recent(limit: int = 10) -> dict:
    safe_limit = min(50, max(1, int(limit)))
    return list_recent_memory_center(limit=safe_limit)


@router.post("/digest")
def memory_digest(payload: MemoryDigestRequest) -> dict:
    return build_memory_daily_digest(payload.date)


@router.get("/digests")
def memory_digests(
    limit: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
    range: str | None = None,
) -> dict:
    safe_limit = min(50, max(1, int(limit)))
    resolved_from, resolved_to = _resolve_digest_range(
        date_from=date_from,
        date_to=date_to,
        range_value=range,
    )
    return list_memory_daily_digests(
        limit=safe_limit,
        date_from=resolved_from,
        date_to=resolved_to,
    )


@router.get("/digests/latest")
def memory_latest_digest(
    date_from: str | None = None,
    date_to: str | None = None,
    range: str | None = None,
) -> dict:
    resolved_from, resolved_to = _resolve_digest_range(
        date_from=date_from,
        date_to=date_to,
        range_value=range,
    )
    result = list_memory_daily_digests(
        limit=1,
        date_from=resolved_from,
        date_to=resolved_to,
    )
    items = result.get("items")
    latest = items[0] if isinstance(items, list) and items else None
    return {
        "ok": latest is not None,
        "item": latest,
    }


@router.post("/sync")
def memory_sync(payload: MemorySyncRequest) -> dict:
    return sync_memory_source(
        payload.source,
        force=payload.force,
        repo=payload.repo,
        page_id=payload.page_id,
    )


def _resolve_digest_range(
    *,
    date_from: str | None,
    date_to: str | None,
    range_value: str | None,
) -> tuple[str | None, str | None]:
    normalized_range = str(range_value or "").strip().lower()
    if normalized_range == "today":
        today = date.today().isoformat()
        return today, today
    if normalized_range == "yesterday":
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        return yesterday, yesterday
    if normalized_range == "7d":
        today = date.today()
        return (today - timedelta(days=6)).isoformat(), today.isoformat()
    if normalized_range == "30d":
        today = date.today()
        return (today - timedelta(days=29)).isoformat(), today.isoformat()
    return date_from, date_to
