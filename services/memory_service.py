from __future__ import annotations

from services.calendar_service import get_events
from services.note_service import get_notes
from services.task_service import get_tasks


def get_memory_snapshot(limit_per_type: int = 5, *, filter_date: str | None = None) -> dict:
    limit = max(1, int(limit_per_type))

    notes = _safe_get_notes(limit=limit)
    tasks = _safe_get_tasks(filter_date=filter_date)
    events = _safe_get_events(filter_date=filter_date)

    return {
        "notes": {
            "count": len(notes),
            "items": notes[:limit],
        },
        "tasks": {
            "count": len(tasks),
            "items": tasks[:limit],
        },
        "events": {
            "count": len(events),
            "items": events[:limit],
        },
    }


def search_memory(query: str, limit_per_type: int = 5) -> dict:
    normalized_query = " ".join(query.lower().strip().split())
    if not normalized_query:
        return {"notes": [], "tasks": [], "events": []}

    limit = max(1, int(limit_per_type))
    note_hits: list[dict] = []
    task_hits: list[dict] = []
    event_hits: list[dict] = []

    for note in _safe_get_notes(limit=100):
        content = str(note.get("content", ""))
        if normalized_query in content.lower():
            note_hits.append(note)
            if len(note_hits) >= limit:
                break

    for task in _safe_get_tasks():
        text = str(task.get("task", ""))
        if normalized_query in text.lower():
            task_hits.append(task)
            if len(task_hits) >= limit:
                break

    for event in _safe_get_events():
        title = str(event.get("title", ""))
        if normalized_query in title.lower():
            event_hits.append(event)
            if len(event_hits) >= limit:
                break

    return {
        "notes": note_hits,
        "tasks": task_hits,
        "events": event_hits,
    }


def _safe_get_notes(*, limit: int) -> list[dict]:
    try:
        return get_notes(limit=limit)
    except Exception:
        return []


def _safe_get_tasks(*, filter_date: str | None = None) -> list[dict]:
    try:
        return get_tasks(filter_date=filter_date)
    except Exception:
        return []


def _safe_get_events(*, filter_date: str | None = None) -> list[dict]:
    try:
        events_result = get_events(filter_date=filter_date)
    except Exception:
        return []
    if not isinstance(events_result, dict):
        return []
    events = events_result.get("events", [])
    if not isinstance(events, list):
        return []
    return events
