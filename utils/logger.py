from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config.settings import INTERACTION_LOG_FILE, VOICE_LOG_FILE


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[LOG {timestamp}] {message}"
    print(line)


def log_voice_event(message: str) -> None:
    _append_line(VOICE_LOG_FILE, "VOICE", message)


def log_interaction_event(event_type: str, payload: dict) -> None:
    enriched_payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": event_type,
        **payload,
    }
    line = json.dumps(enriched_payload, ensure_ascii=False)
    print(f"[INTERACTION] {line}")
    _append_raw_line(INTERACTION_LOG_FILE, line)


def _append_line(path_str: str, prefix: str, message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{prefix} {timestamp}] {message}"
    print(line)
    _append_raw_line(path_str, line)


def _append_raw_line(path_str: str, line: str) -> None:
    log_path = Path(path_str)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(line + "\n")
