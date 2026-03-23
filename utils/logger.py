from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config.settings import VOICE_LOG_FILE


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[LOG {timestamp}] {message}"
    print(line)


def log_voice_event(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[VOICE {timestamp}] {message}"
    print(line)

    log_path = Path(VOICE_LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(line + "\n")
