from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from config.settings import AVATAR_STATE_FILE
from repositories.event_repository import EventRepository
from repositories.task_repository import TaskRepository


@dataclass
class RepositoryTaskPortAdapter:
    repository: TaskRepository

    def create_task(self, task_text: str, dt: str | None = None) -> dict:
        return self.repository.create(task_text, dt=dt).model_dump()

    def list_open_tasks(self, filter_date: str | None = None) -> list[dict]:
        return [item.model_dump() for item in self.repository.list_all(filter_date=filter_date)]

    def mark_task_completed(self, task_id: int) -> dict | None:
        item = self.repository.mark_completed(task_id)
        return item.model_dump() if item else None

    def delete_task(self, task_id: int) -> bool:
        return self.repository.delete(task_id)

    def delete_tasks_by_date(self, filter_date: str) -> int:
        return self.repository.delete_by_date(filter_date)

    def count_open_tasks(self) -> int:
        return self.repository.count_open()

    def delete_all_open_tasks(self) -> int:
        return self.repository.delete_all_open()


@dataclass
class RepositoryCalendarPortAdapter:
    repository: EventRepository

    def create_event(self, title: str, dt: str | None = None) -> dict:
        return self.repository.create(title=title, dt=dt).model_dump()

    def list_events(self, filter_date: str | None = None) -> list[dict]:
        events = [item.model_dump() for item in self.repository.list_all()]
        if not filter_date:
            return events
        return [
            item
            for item in events
            if isinstance(item.get("datetime"), str) and str(item["datetime"]).startswith(filter_date)
        ]

    def delete_event(self, event_id: int) -> bool:
        return self.repository.delete(event_id)


@dataclass
class JsonFileStoragePortAdapter:
    path: Path

    def get_state(self, key: str, default=None):
        payload = self._load()
        return payload.get(key, default)

    def set_state(self, key: str, value) -> None:
        payload = self._load()
        payload[key] = value
        self._save(payload)

    def delete_state(self, key: str) -> bool:
        payload = self._load()
        if key not in payload:
            return False
        payload.pop(key, None)
        self._save(payload)
        return True

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def default_storage_adapter() -> JsonFileStoragePortAdapter:
    return JsonFileStoragePortAdapter(path=Path(AVATAR_STATE_FILE))
