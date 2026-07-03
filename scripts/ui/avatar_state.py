from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


def load_widget_state(state_path: Path | str) -> dict:
    path = Path(state_path)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_saved_position(state_path: Path | str) -> tuple[int, int] | None:
    payload = load_widget_state(state_path)
    x = payload.get("x")
    y = payload.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        return None
    return x, y


def widget_visible_on_start(state_path: Path | str) -> bool:
    payload = load_widget_state(state_path)
    return not bool(payload.get("start_hidden", False))


def save_widget_state(
    state_path: Path | str,
    payload: dict,
    *,
    on_error: Callable[[OSError], None] | None = None,
) -> bool:
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError as exc:
        if on_error is not None:
            on_error(exc)
        return False
    return True
