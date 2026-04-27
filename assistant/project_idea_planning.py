from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class PendingProjectIdeaPlan:
    base_idea: str
    note_title: str | None
    answers: dict[str, str]
    step_index: int = 0


class ProjectIdeaPlanningStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._pending: PendingProjectIdeaPlan | None = None

    def start(self, *, base_idea: str, note_title: str | None = None) -> None:
        with self._lock:
            self._pending = PendingProjectIdeaPlan(
                base_idea=base_idea,
                note_title=note_title,
                answers={},
                step_index=0,
            )

    def get(self) -> PendingProjectIdeaPlan | None:
        with self._lock:
            return self._pending

    def update(self, *, answers: dict[str, str], step_index: int) -> None:
        with self._lock:
            current = self._pending
            if current is None:
                return
            self._pending = PendingProjectIdeaPlan(
                base_idea=current.base_idea,
                note_title=current.note_title,
                answers=dict(answers),
                step_index=step_index,
            )

    def clear(self) -> None:
        with self._lock:
            self._pending = None


project_idea_planning_store = ProjectIdeaPlanningStore()
