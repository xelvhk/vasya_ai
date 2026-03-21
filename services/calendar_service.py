from config.settings import GOOGLE_CALENDAR_ENABLED, GOOGLE_CALENDAR_SYNC_ON_READ
from repositories.event_repository import EventRepository
from services.google_calendar_client import (
    GoogleCalendarError,
    create_google_calendar_event,
    list_google_calendar_events,
)


_event_repository = EventRepository()


def create_event(title: str, dt: str | None = None) -> dict:
    source = "local"
    external_id = None
    google_sync_error = None

    if GOOGLE_CALENDAR_ENABLED and dt:
        try:
            external_id = create_google_calendar_event(title=title, dt=dt)
            source = "google_calendar"
        except GoogleCalendarError as exc:
            source = "local"
            external_id = None
            google_sync_error = str(exc)

    event = _event_repository.create(
        title=title,
        dt=dt,
        source=source,
        external_id=external_id,
    ).model_dump()
    if google_sync_error:
        event["google_sync_error"] = google_sync_error

    return event


def get_events(filter_date: str | None = None) -> dict:
    google_sync_error = None

    if GOOGLE_CALENDAR_ENABLED and GOOGLE_CALENDAR_SYNC_ON_READ:
        try:
            google_events = list_google_calendar_events()
            for item in google_events:
                _event_repository.upsert_external_event(
                    title=item["title"],
                    dt=item["datetime"],
                    source=item["source"],
                    external_id=item["external_id"],
                )
        except GoogleCalendarError as exc:
            google_sync_error = str(exc)

    events = [event.model_dump() for event in _event_repository.list_all()]
    if filter_date:
        events = [
            event
            for event in events
            if isinstance(event.get("datetime"), str)
            and event["datetime"].startswith(filter_date)
        ]

    return {
        "events": events,
        "google_sync_error": google_sync_error,
    }


def delete_event(event_id: int) -> bool:
    return _event_repository.delete(event_id)
