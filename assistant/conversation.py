from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str


class ConversationMemory:
    def __init__(self, limit: int = 6) -> None:
        self._messages: deque[ConversationMessage] = deque(maxlen=limit)

    def add_user(self, content: str) -> None:
        self._messages.append(ConversationMessage(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        self._messages.append(ConversationMessage(role="assistant", content=content))

    def recent(self) -> list[ConversationMessage]:
        return list(self._messages)


conversation_memory = ConversationMemory()
