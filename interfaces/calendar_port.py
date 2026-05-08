from __future__ import annotations

from typing import Protocol


class CalendarPort(Protocol):
    def create_event(self, title: str, dt: str | None = None) -> dict: ...

    def list_events(self, filter_date: str | None = None) -> list[dict]: ...

    def delete_event(self, event_id: int) -> bool: ...
