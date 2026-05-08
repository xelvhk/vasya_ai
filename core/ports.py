from __future__ import annotations

from dataclasses import dataclass

from interfaces.calendar_port import CalendarPort
from interfaces.storage_port import StoragePort
from interfaces.task_port import TaskPort
from repositories.event_repository import EventRepository
from repositories.task_repository import TaskRepository
from services.ports_adapters import (
    RepositoryCalendarPortAdapter,
    RepositoryTaskPortAdapter,
    default_storage_adapter,
)


@dataclass(frozen=True)
class AppPorts:
    task: TaskPort
    calendar: CalendarPort
    storage: StoragePort


def build_default_ports() -> AppPorts:
    return AppPorts(
        task=RepositoryTaskPortAdapter(repository=TaskRepository()),
        calendar=RepositoryCalendarPortAdapter(repository=EventRepository()),
        storage=default_storage_adapter(),
    )
