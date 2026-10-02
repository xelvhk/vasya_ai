"""Durable, private outbox for transcripts awaiting the Mac Obsidian writer."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, urlsplit

from config.settings import APP_PATHS
from services.video_note_service import validate_video_note_input


class VideoNoteQueueConflict(ValueError):
    pass


def queue_path() -> Path:
    configured = os.getenv("VASYA_VIDEO_NOTE_QUEUE_FILE", "").strip()
    return Path(configured).expanduser() if configured else APP_PATHS.state_file("video_note_queue.db")


def queue_enabled() -> bool:
    return os.getenv("VASYA_VIDEO_NOTE_QUEUE_MODE", "").strip().lower() in {"1", "true", "yes"}


def enqueue_video_note(payload: dict, *, path: Path | None = None) -> dict:
    validate_video_note_input(**payload)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    revision = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    target = path or queue_path()
    with closing(_connect(target)) as connection, connection:
        connection.execute(
            """INSERT INTO video_notes
               (video_id, revision, payload_json, status, updated_at)
               VALUES (?, ?, ?, 'queued', ?)
               ON CONFLICT(video_id) DO UPDATE SET
                   revision = excluded.revision,
                   payload_json = excluded.payload_json,
                   status = 'queued', relative_path = NULL, url = NULL,
                   updated_at = excluded.updated_at
               WHERE video_notes.revision != excluded.revision""",
            (payload["video_id"], revision, encoded, datetime.now(timezone.utc).isoformat()),
        )
        row = connection.execute(
            "SELECT status, relative_path, url FROM video_notes WHERE video_id = ?",
            (payload["video_id"],),
        ).fetchone()
    return {
        "video_id": payload["video_id"], "status": row["status"],
        "relative_path": row["relative_path"], "url": row["url"],
    }


def list_pending_video_notes(*, path: Path | None = None, limit: int = 50) -> list[dict]:
    with closing(_connect(path or queue_path())) as connection:
        rows = connection.execute(
            """SELECT revision, payload_json FROM video_notes
               WHERE status = 'queued' ORDER BY updated_at LIMIT ?""",
            (min(max(limit, 1), 100),),
        ).fetchall()
    return [{"revision": row["revision"], **json.loads(row["payload_json"])} for row in rows]


def complete_video_note(
    video_id: str, revision: str, relative_path: str, url: str, *, path: Path | None = None,
) -> dict:
    expected = f"30_Knowledge/Video/video-{video_id[:20]}.md"
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    if (
        relative_path != expected
        or parsed.scheme != "obsidian"
        or parsed.netloc != "open"
        or query.get("file") != [expected]
        or not query.get("vault", [""])[0]
    ):
        raise VideoNoteQueueConflict("Invalid saved note location")
    with closing(_connect(path or queue_path())) as connection, connection:
        cursor = connection.execute(
            """UPDATE video_notes SET status = 'saved', relative_path = ?, url = ?,
               updated_at = ? WHERE video_id = ? AND revision = ?""",
            (relative_path, url, datetime.now(timezone.utc).isoformat(), video_id, revision),
        )
        if cursor.rowcount != 1:
            raise VideoNoteQueueConflict("Queued note revision changed or does not exist")
    return {"video_id": video_id, "status": "saved", "relative_path": relative_path, "url": url}


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS video_notes (
            video_id TEXT PRIMARY KEY, revision TEXT NOT NULL, payload_json TEXT NOT NULL,
            status TEXT NOT NULL, relative_path TEXT, url TEXT, updated_at TEXT NOT NULL
        )"""
    )
    os.chmod(path, 0o600)
    return connection
