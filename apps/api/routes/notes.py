from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas import CreateNoteRequest
from services.note_service import create_note, get_notes


router = APIRouter(prefix="/v1/notes", tags=["notes"])


@router.get("")
def list_notes(limit: int = 20) -> dict:
    safe_limit = min(100, max(1, int(limit)))
    return {"items": get_notes(limit=safe_limit)}


@router.post("")
def add_note(payload: CreateNoteRequest) -> dict:
    note = create_note(payload.content.strip())
    return {"item": note}

