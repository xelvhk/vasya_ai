import json
import os
from config.settings import CALENDAR_STORAGE_FILE

def _load_events() -> list:
    if not os.path.exists(CALENDAR_STORAGE_FILE):
        return []

    with open(CALENDAR_STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_events(events: list) -> None:
    with open(CALENDAR_STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def create_event(title: str, dt: str | None = None) -> dict:
    events = _load_events()
    event = {
        "title": title,
        "datetime": dt,
    }
    events.append(event)
    _save_events(events)
    return event

def get_events() -> list:
    return _load_events()