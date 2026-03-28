from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ActiveGame:
    game: str
    state: dict


class GameStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._active: ActiveGame | None = None

    def set(self, game: str, state: dict | None = None) -> None:
        with self._lock:
            self._active = ActiveGame(game=game, state=state or {})

    def get(self) -> ActiveGame | None:
        with self._lock:
            return self._active

    def clear(self) -> None:
        with self._lock:
            self._active = None


game_store = GameStore()
