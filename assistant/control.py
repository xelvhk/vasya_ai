from __future__ import annotations

from enum import Enum
from threading import Lock


class AssistantControlAction(str, Enum):
    NONE = "none"
    EXIT = "exit"
    OPEN_TEXT_COMMAND = "open_text_command"


class AssistantControlStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._action = AssistantControlAction.NONE

    def request_exit(self) -> None:
        with self._lock:
            self._action = AssistantControlAction.EXIT

    def request_open_text_command(self) -> None:
        with self._lock:
            self._action = AssistantControlAction.OPEN_TEXT_COMMAND

    def consume_action(self) -> AssistantControlAction:
        with self._lock:
            action = self._action
            self._action = AssistantControlAction.NONE
            return action


assistant_control = AssistantControlStore()
