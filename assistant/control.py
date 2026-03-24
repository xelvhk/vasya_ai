from __future__ import annotations

from enum import Enum
from threading import Lock


class AssistantControlAction(str, Enum):
    NONE = "none"
    EXIT = "exit"


class AssistantControlStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._action = AssistantControlAction.NONE

    def request_exit(self) -> None:
        with self._lock:
            self._action = AssistantControlAction.EXIT

    def consume_action(self) -> AssistantControlAction:
        with self._lock:
            action = self._action
            self._action = AssistantControlAction.NONE
            return action


assistant_control = AssistantControlStore()
