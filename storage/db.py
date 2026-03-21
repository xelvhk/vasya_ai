from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime

from config.settings import CALENDAR_STORAGE_FILE, STORAGE_DB_FILE, TASK_STORAGE_FILE


def get_connection() -> sqlite3.Connection:
    _ensure_storage_dir()
    connection = sqlite3.connect(STORAGE_DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                source TEXT NOT NULL DEFAULT 'local',
                external_id TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                datetime TEXT,
                source TEXT NOT NULL DEFAULT 'local',
                external_id TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

    _migrate_legacy_json_if_needed()


def _migrate_legacy_json_if_needed() -> None:
    with get_connection() as connection:
        tasks_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        events_count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]

        if tasks_count == 0:
            for item in _load_legacy_items(TASK_STORAGE_FILE):
                task_text = item.get("task")
                if not task_text:
                    continue
                connection.execute(
                    """
                    INSERT INTO tasks (task, status, source, external_id, created_at)
                    VALUES (?, 'open', 'legacy_json', NULL, ?)
                    """,
                    (task_text, _current_timestamp()),
                )

        if events_count == 0:
            for item in _load_legacy_items(CALENDAR_STORAGE_FILE):
                title = item.get("title")
                if not title:
                    continue
                connection.execute(
                    """
                    INSERT INTO events (title, datetime, source, external_id, created_at)
                    VALUES (?, ?, 'legacy_json', NULL, ?)
                    """,
                    (title, item.get("datetime"), _current_timestamp()),
                )


def _load_legacy_items(file_path: str) -> list[dict]:
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

    return data if isinstance(data, list) else []


def _ensure_storage_dir() -> None:
    storage_dir = os.path.dirname(STORAGE_DB_FILE)
    if storage_dir:
        os.makedirs(storage_dir, exist_ok=True)


def _current_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_timestamp() -> str:
    return _current_timestamp()
