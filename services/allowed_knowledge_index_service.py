from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sqlite3

from config.settings import APP_PATHS
from services.allowed_knowledge_service import (
    AllowedNote,
    KnowledgeSearchResult,
    collect_allowed_notes,
    rank_allowed_notes,
    resolve_knowledge_vault_path,
)


@dataclass(frozen=True)
class IndexSyncReport:
    added: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0
    observed_at: datetime | None = None
    error: str | None = None


def sync_allowed_index(
    *, vault_path: Path | None = None, index_path: Path | None = None
) -> IndexSyncReport:
    vault = (vault_path or resolve_knowledge_vault_path()).expanduser()
    notes, error = collect_allowed_notes(vault)
    if error:
        return IndexSyncReport(error=error)

    path = _index_path(index_path)
    vault_id = _vault_id(vault)
    observed_at = datetime.now(timezone.utc)
    added = updated = deleted = unchanged = 0
    with closing(_connect(path)) as connection, connection:
        existing = {
            row["relative_path"]: (row["content_hash"], row["modified_at"])
            for row in connection.execute(
                "SELECT relative_path, content_hash, modified_at FROM knowledge_documents WHERE vault_id = ?",
                (vault_id,),
            )
        }
        seen: set[str] = set()
        for note in notes:
            seen.add(note.relative_path)
            content_hash = hashlib.sha256(note.content.encode("utf-8")).hexdigest()
            if existing.get(note.relative_path) == (content_hash, note.modified_at.isoformat()):
                unchanged += 1
                continue
            connection.execute(
                """
                INSERT INTO knowledge_documents
                    (vault_id, relative_path, title, content, content_hash, modified_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(vault_id, relative_path) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    content_hash = excluded.content_hash,
                    modified_at = excluded.modified_at
                """,
                (
                    vault_id,
                    note.relative_path,
                    note.title,
                    note.content,
                    content_hash,
                    note.modified_at.isoformat(),
                ),
            )
            if note.relative_path in existing:
                updated += 1
            else:
                added += 1
        for relative_path in existing.keys() - seen:
            connection.execute(
                "DELETE FROM knowledge_documents WHERE vault_id = ? AND relative_path = ?",
                (vault_id, relative_path),
            )
            deleted += 1
        connection.execute(
            """
            INSERT INTO knowledge_sync_state (vault_id, observed_at) VALUES (?, ?)
            ON CONFLICT(vault_id) DO UPDATE SET observed_at = excluded.observed_at
            """,
            (vault_id, observed_at.isoformat()),
        )
    return IndexSyncReport(added, updated, deleted, unchanged, observed_at)


def search_indexed_notes(
    query: str,
    *,
    vault_path: Path | None = None,
    index_path: Path | None = None,
    refresh_after_seconds: int | None = 60,
    limit: int = 3,
) -> KnowledgeSearchResult:
    vault = (vault_path or resolve_knowledge_vault_path()).expanduser()
    path = _index_path(index_path)
    vault_id = _vault_id(vault)
    with closing(_connect(path)) as connection:
        row = connection.execute(
            "SELECT observed_at FROM knowledge_sync_state WHERE vault_id = ?", (vault_id,)
        ).fetchone()
    observed_at = datetime.fromisoformat(row["observed_at"]) if row else None
    sync_error = None
    if refresh_after_seconds is not None and (
        observed_at is None
        or (datetime.now(timezone.utc) - observed_at).total_seconds() >= refresh_after_seconds
    ):
        report = sync_allowed_index(vault_path=vault, index_path=path)
        sync_error = report.error
        observed_at = report.observed_at or observed_at
    if observed_at is None:
        return KnowledgeSearchResult((), sync_error or "Индекс заметок ещё не создан.")

    with closing(_connect(path)) as connection:
        rows = connection.execute(
            """
            SELECT relative_path, title, content, modified_at
            FROM knowledge_documents WHERE vault_id = ?
            """,
            (vault_id,),
        ).fetchall()
    notes = tuple(
        AllowedNote(
            relative_path=row["relative_path"],
            title=row["title"],
            content=row["content"],
            modified_at=datetime.fromisoformat(row["modified_at"]),
        )
        for row in rows
    )
    return KnowledgeSearchResult(
        rank_allowed_notes(query, notes, vault=vault, limit=limit),
        stale=sync_error is not None,
        observed_at=observed_at,
    )


def _index_path(index_path: Path | None) -> Path:
    configured = os.getenv("VASYA_KNOWLEDGE_INDEX_FILE", "").strip()
    return Path(index_path or configured or APP_PATHS.state_file("allowed_knowledge_index.db")).expanduser()


def _vault_id(vault: Path) -> str:
    return hashlib.sha256(str(vault.resolve()).encode("utf-8")).hexdigest()


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            vault_id TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            PRIMARY KEY (vault_id, relative_path)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_sync_state (
            vault_id TEXT PRIMARY KEY,
            observed_at TEXT NOT NULL
        )
        """
    )
    return connection
