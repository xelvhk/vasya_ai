from __future__ import annotations

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
) -> dict:
    safe_limit = min(50, max(1, int(limit)))
    return list_memory_daily_digests(
        limit=safe_limit,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/sync")
def memory_sync(payload: MemorySyncRequest) -> dict:
    return sync_memory_source(
        payload.source,
        force=payload.force,
        repo=payload.repo,
        page_id=payload.page_id,
    )
