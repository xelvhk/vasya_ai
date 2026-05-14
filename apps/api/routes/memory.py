from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas import MemorySyncRequest
from services.memory_center_service import get_memory_center_status
from services.memory_sync_service import sync_memory_source


router = APIRouter(prefix="/v1/memory", tags=["memory"])


@router.get("/status")
def memory_status() -> dict:
    return get_memory_center_status()


@router.post("/sync")
def memory_sync(payload: MemorySyncRequest) -> dict:
    return sync_memory_source(
        payload.source,
        force=payload.force,
        repo=payload.repo,
        page_id=payload.page_id,
    )
