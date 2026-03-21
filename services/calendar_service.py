from config.settings import GOOGLE_CALENDAR_ENABLED
from repositories.event_repository import EventRepository
from services.google_calendar_client import GoogleCalendarError, create_google_calendar_event


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


def get_events() -> list:
    return [event.model_dump() for event in _event_repository.list_all()]
