from datetime import datetime

from core.models import CalendarEvent
from storage.db import current_timestamp, get_connection, initialize_database


class EventRepository:
    def create(
        self,
        title: str,
        dt: str | None = None,
        source: str = "local",
        external_id: str | None = None,
    ) -> CalendarEvent:
        initialize_database()

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (title, datetime, source, external_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, dt, source, external_id, current_timestamp()),
            )
            row = connection.execute(
                """
                SELECT id, title, datetime, source, external_id, created_at
                FROM events
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

        return CalendarEvent(**dict(row))

    def list_all(self) -> list[CalendarEvent]:
        return self.list_upcoming()

    def list_upcoming(self, now: datetime | None = None) -> list[CalendarEvent]:
        initialize_database()
        current_time = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, title, datetime, source, external_id, created_at
                FROM events
                WHERE datetime IS NULL OR datetime >= ?
                ORDER BY datetime IS NULL, datetime ASC, id ASC
                """,
                (current_time,),
            ).fetchall()

        return [CalendarEvent(**dict(row)) for row in rows]

    def upsert_external_event(
        self,
        title: str,
        dt: str | None,
        source: str,
        external_id: str,
    ) -> CalendarEvent:
        initialize_database()

        with get_connection() as connection:
            existing_row = connection.execute(
                """
                SELECT id
                FROM events
                WHERE source = ? AND external_id = ?
                """,
                (source, external_id),
            ).fetchone()

            if existing_row:
                connection.execute(
                    """
                    UPDATE events
                    SET title = ?, datetime = ?
                    WHERE id = ?
                    """,
                    (title, dt, existing_row["id"]),
                )
                row = connection.execute(
                    """
                    SELECT id, title, datetime, source, external_id, created_at
                    FROM events
                    WHERE id = ?
                    """,
                    (existing_row["id"],),
                ).fetchone()
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO events (title, datetime, source, external_id, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (title, dt, source, external_id, current_timestamp()),
                )
                row = connection.execute(
                    """
                    SELECT id, title, datetime, source, external_id, created_at
                    FROM events
                    WHERE id = ?
                    """,
                    (cursor.lastrowid,),
                ).fetchone()

        return CalendarEvent(**dict(row))

    def delete(self, event_id: int) -> bool:
        initialize_database()

        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM events WHERE id = ?", (event_id,))

        return cursor.rowcount > 0
