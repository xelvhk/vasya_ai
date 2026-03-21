from repositories.event_repository import EventRepository


_event_repository = EventRepository()


def create_event(title: str, dt: str | None = None) -> dict:
    return _event_repository.create(title=title, dt=dt).model_dump()


def get_events() -> list:
    return [event.model_dump() for event in _event_repository.list_all()]
