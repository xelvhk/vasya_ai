"""Local file mailbox between the API process and desktop radio owner."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path


def _directory(root: Path) -> Path:
    directory = root / "focus_radio"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory


def _write_json(path: Path, payload: dict) -> None:
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def write_status(root: Path, snapshot: dict) -> None:
    _write_json(_directory(root) / "status.json", {**snapshot, "updated_at": time.time()})


def read_status(root: Path, *, now: float | None = None) -> dict:
    try:
        status = json.loads((root / "focus_radio" / "status.json").read_text(encoding="utf-8"))
        age = (time.time() if now is None else now) - float(status["updated_at"])
        if not 0 <= age <= 5:
            return {"available": False}
        return {"available": True, **status}
    except (OSError, ValueError, KeyError, TypeError):
        return {"available": False}


def enqueue_command(root: Path, command: dict) -> None:
    directory = _directory(root) / "commands"
    directory.mkdir(mode=0o700, exist_ok=True)
    filename = f"{time.time_ns():020d}-{uuid.uuid4().hex}.json"
    _write_json(directory / filename, command)


def take_commands(root: Path, *, since: float = 0) -> list[dict]:
    directory = root / "focus_radio" / "commands"
    if not directory.exists():
        return []
    commands = []
    for path in sorted(directory.glob("*.json")):
        try:
            if path.stat().st_mtime >= since:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    commands.append(value)
        except (OSError, ValueError):
            pass
        finally:
            path.unlink(missing_ok=True)
    return commands
