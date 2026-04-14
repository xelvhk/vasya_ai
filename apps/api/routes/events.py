from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas import CreateEventRequest
from services.calendar_service import create_event, get_events


router = APIRouter(prefix="/v1/events", tags=["events"])


@router.get("")
def list_events(date: str | None = None) -> dict:
    return get_events(filter_date=date)


@router.post("")
def add_event(payload: CreateEventRequest) -> dict:
    event = create_event(payload.title.strip(), dt=payload.datetime)
    return {"item": event}

