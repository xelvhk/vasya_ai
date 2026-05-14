from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

from config.settings import MEMORY_SYNC_INTERVAL_SECONDS, MEMORY_WIKI_DIR
from storage.db import current_timestamp, get_connection, initialize_database


@dataclass(frozen=True)
class MemoryChunk:
    id: int
    source_key: str
    title: str
    content_hash: str
    markdown_path: str
    external_id: str | None
    url: str | None
    tags: tuple[str, ...]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SyncDecision:
    due: bool
    toolkit: str
    connection_id: str
    last_synced_at_ts: int | None
    next_sync_at_ts: int | None
    cursor: str | None
    last_error: str | None


class MemoryCenterService:
    def __init__(self, *, wiki_dir: str | Path | None = None) -> None:
        self.wiki_dir = Path(wiki_dir or MEMORY_WIKI_DIR).expanduser()

    def ingest_text(
        self,
        *,
        source_key: str,
        source_name: str,
        title: str,
        content: str,
        external_id: str | None = None,
        url: str | None = None,
        tags: tuple[str, ...] = (),
        source_kind: str = "manual",
    ) -> MemoryChunk:
        safe_source_key = _normalize_key(source_key)
        safe_title = _clean_text(title) or "Untitled memory"
        clean_content = _clean_text(content)
        if not safe_source_key:
            raise ValueError("source_key is required")
        if not clean_content:
            raise ValueError("content is required")

        initialize_database()
        now = current_timestamp()
        content_hash = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()
        dedupe_external_id = external_id or content_hash
        markdown_path = self._markdown_path(
            source_key=safe_source_key,
            title=safe_title,
            external_id=dedupe_external_id,
            content_hash=content_hash,
        )
        self._write_markdown(
            path=markdown_path,
            source_key=safe_source_key,
            title=safe_title,
            content=clean_content,
            external_id=external_id,
            url=url,
            tags=tags,
            content_hash=content_hash,
        )

        with get_connection() as connection:
            source_id = _upsert_source(
                connection,
                source_key=safe_source_key,
                name=_clean_text(source_name) or safe_source_key,
                kind=_normalize_key(source_kind) or "manual",
                timestamp=now,
            )
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO memory_chunks (
                        source_id, source_key, external_id, title, content_hash,
                        markdown_path, url, tags, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        safe_source_key,
                        dedupe_external_id,
                        safe_title,
                        content_hash,
                        str(markdown_path),
                        url,
                        json.dumps(list(tags), ensure_ascii=False),
                        now,
                        now,
                    ),
                )
                chunk_id = int(cursor.lastrowid)
            except sqlite3.IntegrityError:
                row = connection.execute(
                    """
                    SELECT id
                    FROM memory_chunks
                    WHERE source_key = ? AND external_id = ?
                    """,
                    (safe_source_key, dedupe_external_id),
                ).fetchone()
                chunk_id = int(row["id"])
                connection.execute(
                    """
                    UPDATE memory_chunks
                    SET title = ?, content_hash = ?, markdown_path = ?, url = ?,
                        tags = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        safe_title,
                        content_hash,
                        str(markdown_path),
                        url,
                        json.dumps(list(tags), ensure_ascii=False),
                        now,
                        chunk_id,
                    ),
                )
            connection.execute(
                """
                UPDATE memory_sources
                SET last_ingested_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, source_id),
            )
            chunk_row = connection.execute(
                """
                SELECT id, source_key, external_id, title, content_hash, markdown_path,
                       url, tags, created_at, updated_at
                FROM memory_chunks
                WHERE id = ?
                """,
                (chunk_id,),
            ).fetchone()

        return _row_to_chunk(chunk_row)

    def get_status(self) -> dict:
        initialize_database()
        with get_connection() as connection:
            source_rows = connection.execute(
                """
                SELECT s.id, s.source_key, s.name, s.kind, s.last_ingested_at,
                       s.created_at, s.updated_at, COUNT(c.id) AS chunks_count
                FROM memory_sources s
                LEFT JOIN memory_chunks c ON c.source_id = s.id
                GROUP BY s.id
                ORDER BY s.updated_at DESC, s.id DESC
                """
            ).fetchall()
            chunks_count = connection.execute(
                "SELECT COUNT(*) FROM memory_chunks"
            ).fetchone()[0]
            latest = connection.execute(
                """
                SELECT id, source_key, external_id, title, content_hash, markdown_path,
                       url, tags, created_at, updated_at
                FROM memory_chunks
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
            sync_rows = connection.execute(
                """
                SELECT toolkit, connection_id, cursor, last_synced_at_ts,
                       last_items_count, last_error, updated_at
                FROM memory_sync_state
                ORDER BY updated_at DESC, id DESC
                LIMIT 25
                """
            ).fetchall()

        sources = [
            {
                "source_key": row["source_key"],
                "name": row["name"],
                "kind": row["kind"],
                "last_ingested_at": row["last_ingested_at"],
                "chunks_count": int(row["chunks_count"]),
            }
            for row in source_rows
        ]
        return {
            "status": "ready" if chunks_count else "empty",
            "wiki_dir": str(self.wiki_dir),
            "sources_count": len(sources),
            "chunks_count": int(chunks_count),
            "sources": sources,
            "sync_connections_count": len(sync_rows),
            "sync_connections": [_sync_row_to_dict(row) for row in sync_rows],
            "latest_chunk": _chunk_to_dict(_row_to_chunk(latest)) if latest else None,
        }

    def _markdown_path(
        self,
        *,
        source_key: str,
        title: str,
        external_id: str,
        content_hash: str,
    ) -> Path:
        slug = _slugify(title)
        suffix = _slugify(external_id) or content_hash[:12]
        return self.wiki_dir / source_key / f"{slug}-{suffix[:32]}.md"

    def _write_markdown(
        self,
        *,
        path: Path,
        source_key: str,
        title: str,
        content: str,
        external_id: str | None,
        url: str | None,
        tags: tuple[str, ...],
        content_hash: str,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tag_lines = "\n".join(f"  - {tag}" for tag in tags)
        frontmatter = [
            "---",
            "type: memory_chunk",
            f"source_key: {source_key}",
            f"title: {_quote_yaml(title)}",
            f"external_id: {external_id or ''}",
            f"url: {url or ''}",
            f"content_hash: {content_hash}",
            "tags:",
            tag_lines or "  - memory",
            "---",
            "",
            f"# {title}",
            "",
            content,
            "",
        ]
        path.write_text("\n".join(frontmatter), encoding="utf-8")


def get_memory_center_status() -> dict:
    return MemoryCenterService().get_status()


def build_memory_center_summary(status: dict) -> str:
    state = str(status.get("status") or "unknown")
    sources_count = int(status.get("sources_count") or 0)
    chunks_count = int(status.get("chunks_count") or 0)
    lines = [
        f"Status: {state}",
        f"Sources: {sources_count}",
        f"Chunks: {chunks_count}",
    ]

    latest = status.get("latest_chunk")
    if isinstance(latest, dict) and latest.get("title"):
        lines.append(f"Latest: {latest.get('title')}")

    sources = status.get("sources")
    if isinstance(sources, list) and sources:
        lines.extend(["", "Sources"])
        for item in sources[:6]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("source_key") or "Source")
            count = int(item.get("chunks_count") or 0)
            last = str(item.get("last_ingested_at") or "never")
            lines.append(f"- {name}: {count} chunks, last {last}")

    sync_connections = status.get("sync_connections")
    if isinstance(sync_connections, list) and sync_connections:
        lines.extend(["", "Sync"])
        for item in sync_connections[:6]:
            if not isinstance(item, dict):
                continue
            toolkit = str(item.get("toolkit") or "source")
            connection_id = str(item.get("connection_id") or "default")
            last_items_count = int(item.get("last_items_count") or 0)
            error = str(item.get("last_error") or "").strip()
            suffix = f", error: {error}" if error else ""
            lines.append(f"- {toolkit}/{connection_id}: {last_items_count} items{suffix}")

    if len(lines) <= 3:
        lines.append("")
        lines.append("Memory Center is empty. Run sync to ingest GitHub, Notion, or Obsidian context.")
    return "\n".join(lines)


class MemorySyncPlanner:
    def __init__(self, *, default_interval_seconds: int | None = None) -> None:
        self.default_interval_seconds = int(
            default_interval_seconds or MEMORY_SYNC_INTERVAL_SECONDS
        )

    def should_sync(
        self,
        toolkit: str,
        connection_id: str,
        *,
        now_ts: int | None = None,
        interval_seconds: int | None = None,
    ) -> SyncDecision:
        initialize_database()
        safe_toolkit = _normalize_key(toolkit)
        safe_connection_id = _normalize_key(connection_id) or "default"
        if not safe_toolkit:
            raise ValueError("toolkit is required")

        current_ts = int(now_ts if now_ts is not None else time.time())
        interval = int(interval_seconds or self.default_interval_seconds)
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT cursor, last_synced_at_ts, last_error
                FROM memory_sync_state
                WHERE toolkit = ? AND connection_id = ?
                """,
                (safe_toolkit, safe_connection_id),
            ).fetchone()

        if not row or row["last_synced_at_ts"] is None:
            return SyncDecision(
                due=True,
                toolkit=safe_toolkit,
                connection_id=safe_connection_id,
                last_synced_at_ts=None,
                next_sync_at_ts=None,
                cursor=row["cursor"] if row else None,
                last_error=row["last_error"] if row else None,
            )

        last_synced_at_ts = int(row["last_synced_at_ts"])
        next_sync_at_ts = last_synced_at_ts + interval
        return SyncDecision(
            due=current_ts >= next_sync_at_ts,
            toolkit=safe_toolkit,
            connection_id=safe_connection_id,
            last_synced_at_ts=last_synced_at_ts,
            next_sync_at_ts=next_sync_at_ts,
            cursor=row["cursor"],
            last_error=row["last_error"],
        )

    def record_success(
        self,
        toolkit: str,
        connection_id: str,
        *,
        cursor: str | None,
        synced_at_ts: int | None = None,
        items_count: int = 0,
    ) -> None:
        self._upsert_state(
            toolkit,
            connection_id,
            cursor=cursor,
            synced_at_ts=synced_at_ts,
            items_count=items_count,
            error=None,
        )

    def record_error(
        self,
        toolkit: str,
        connection_id: str,
        *,
        error: str,
        synced_at_ts: int | None = None,
    ) -> None:
        self._upsert_state(
            toolkit,
            connection_id,
            cursor=None,
            synced_at_ts=synced_at_ts,
            items_count=0,
            error=_clean_text(error)[:500],
        )

    def _upsert_state(
        self,
        toolkit: str,
        connection_id: str,
        *,
        cursor: str | None,
        synced_at_ts: int | None,
        items_count: int,
        error: str | None,
    ) -> None:
        initialize_database()
        safe_toolkit = _normalize_key(toolkit)
        safe_connection_id = _normalize_key(connection_id) or "default"
        if not safe_toolkit:
            raise ValueError("toolkit is required")

        now = current_timestamp()
        ts = int(synced_at_ts if synced_at_ts is not None else time.time())
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO memory_sync_state (
                    toolkit, connection_id, cursor, last_synced_at_ts,
                    last_items_count, last_error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(toolkit, connection_id) DO UPDATE SET
                    cursor = COALESCE(excluded.cursor, memory_sync_state.cursor),
                    last_synced_at_ts = excluded.last_synced_at_ts,
                    last_items_count = excluded.last_items_count,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (
                    safe_toolkit,
                    safe_connection_id,
                    cursor,
                    ts,
                    max(0, int(items_count)),
                    error,
                    now,
                    now,
                ),
            )


def _upsert_source(
    connection: sqlite3.Connection,
    *,
    source_key: str,
    name: str,
    kind: str,
    timestamp: str,
) -> int:
    connection.execute(
        """
        INSERT INTO memory_sources (source_key, name, kind, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(source_key) DO UPDATE SET
            name = excluded.name,
            kind = excluded.kind,
            updated_at = excluded.updated_at
        """,
        (source_key, name, kind, timestamp, timestamp),
    )
    row = connection.execute(
        "SELECT id FROM memory_sources WHERE source_key = ?",
        (source_key,),
    ).fetchone()
    return int(row["id"])


def _row_to_chunk(row: sqlite3.Row) -> MemoryChunk:
    raw_tags = row["tags"] or "[]"
    try:
        loaded_tags = json.loads(raw_tags)
    except json.JSONDecodeError:
        loaded_tags = []
    tags = tuple(str(item) for item in loaded_tags if str(item).strip())
    return MemoryChunk(
        id=int(row["id"]),
        source_key=str(row["source_key"]),
        title=str(row["title"]),
        content_hash=str(row["content_hash"]),
        markdown_path=str(row["markdown_path"]),
        external_id=row["external_id"],
        url=row["url"],
        tags=tags,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _chunk_to_dict(chunk: MemoryChunk) -> dict:
    return {
        "id": chunk.id,
        "source_key": chunk.source_key,
        "title": chunk.title,
        "content_hash": chunk.content_hash,
        "markdown_path": chunk.markdown_path,
        "external_id": chunk.external_id,
        "url": chunk.url,
        "tags": list(chunk.tags),
        "created_at": chunk.created_at,
        "updated_at": chunk.updated_at,
    }


def _sync_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "toolkit": row["toolkit"],
        "connection_id": row["connection_id"],
        "cursor": row["cursor"],
        "last_synced_at_ts": row["last_synced_at_ts"],
        "last_items_count": int(row["last_items_count"] or 0),
        "last_error": row["last_error"],
        "updated_at": row["updated_at"],
    }


def _clean_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", str(value or "").strip().lower()).strip("_")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ_-]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:80] or "memory"


def _quote_yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
