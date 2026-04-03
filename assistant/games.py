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
        self._last_game: str | None = None

    def set(self, game: str, state: dict | None = None) -> None:
        with self._lock:
            self._active = ActiveGame(game=game, state=state or {})
            self._last_game = game

    def get(self) -> ActiveGame | None:
        with self._lock:
            return self._active

    def get_last_game(self) -> str | None:
        with self._lock:
            return self._last_game

    def clear(self) -> None:
        with self._lock:
            self._active = None


game_store = GameStore()
