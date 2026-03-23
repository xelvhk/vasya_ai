from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Callable


class AssistantStateName(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass(frozen=True)
class AssistantState:
    name: AssistantStateName
    message: str | None = None


class AssistantStateStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._state = AssistantState(AssistantStateName.IDLE)
        self._subscribers: list[Callable[[AssistantState], None]] = []

    def get(self) -> AssistantState:
        with self._lock:
            return self._state

    def set(self, name: AssistantStateName, message: str | None = None) -> None:
        with self._lock:
            self._state = AssistantState(name=name, message=message)
            subscribers = list(self._subscribers)

        for callback in subscribers:
            callback(self._state)

    def subscribe(self, callback: Callable[[AssistantState], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)


assistant_state = AssistantStateStore()
