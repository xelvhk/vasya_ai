from __future__ import annotations

import re
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class PendingConfirmation:
    kind: str
    payload: dict


class ConfirmationStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._pending: PendingConfirmation | None = None

    def set(self, kind: str, payload: dict | None = None) -> None:
        with self._lock:
            self._pending = PendingConfirmation(kind=kind, payload=payload or {})

    def get(self) -> PendingConfirmation | None:
        with self._lock:
            return self._pending

    def clear(self) -> None:
        with self._lock:
            self._pending = None


confirmation_store = ConfirmationStore()


AFFIRMATIVE_PHRASES = {
    "да",
    "ага",
    "угу",
    "подтверждаю",
    "подтверди",
    "подтверждаю удаление",
    "удаляй",
    "удали",
    "подтверждаю, удаляй",
}

NEGATIVE_PHRASES = {
    "нет",
    "не надо",
    "отмена",
    "отмени",
    "не удаляй",
    "не удалять",
    "стоп",
}


def classify_confirmation_reply(user_text: str) -> str | None:
    normalized = _normalize_confirmation_text(user_text)
    if normalized in AFFIRMATIVE_PHRASES:
        return "confirm"
    if normalized in NEGATIVE_PHRASES:
        return "cancel"
    if normalized.startswith(("да ", "ага ", "угу ", "подтверждаю ", "удаляй ", "удали ")):
        return "confirm"
    if normalized.startswith(("нет ", "не надо ", "отмена ", "отмени ", "не удаляй ")):
        return "cancel"
    return None


def _normalize_confirmation_text(user_text: str) -> str:
    normalized = user_text.lower().strip()
    normalized = normalized.replace("ё", "е")
    normalized = re.sub(r"[^\w\s]+", " ", normalized)
    normalized = " ".join(normalized.split())
    return normalized
