from core.models import NoteItem
from storage.db import current_timestamp, get_connection, initialize_database


class NoteRepository:
    def create(self, content: str, source: str = "local") -> NoteItem:
        initialize_database()

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO notes (content, source, created_at)
                VALUES (?, ?, ?)
                """,
                (content, source, current_timestamp()),
            )
            row = connection.execute(
                """
                SELECT id, content, source, created_at
                FROM notes
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

        return NoteItem(**dict(row))

    def list_recent(self, limit: int = 10) -> list[NoteItem]:
        initialize_database()

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, content, source, created_at
                FROM notes
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [NoteItem(**dict(row)) for row in rows]
