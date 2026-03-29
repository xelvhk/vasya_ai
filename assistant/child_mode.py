from __future__ import annotations

import json
from pathlib import Path

from config.settings import CHILD_MODE_STATE_FILE


class ChildModeStore:
    def __init__(self) -> None:
        self._enabled: bool | None = None

    def is_enabled(self) -> bool:
        if self._enabled is None:
            self._enabled = self._load()
        return self._enabled

    def enable(self) -> bool:
        previous = self.is_enabled()
        self._enabled = True
        self._save(True)
        return not previous

    def disable(self) -> bool:
        previous = self.is_enabled()
        self._enabled = False
        self._save(False)
        return previous

    def _load(self) -> bool:
        state_path = Path(CHILD_MODE_STATE_FILE)
        if not state_path.exists():
            return False
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        return bool(data.get("enabled"))

    def _save(self, enabled: bool) -> None:
        state_path = Path(CHILD_MODE_STATE_FILE)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"enabled": enabled}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


child_mode_store = ChildModeStore()
