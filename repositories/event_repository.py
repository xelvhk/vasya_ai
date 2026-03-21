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
        initialize_database()

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, title, datetime, source, external_id, created_at
                FROM events
                ORDER BY id ASC
                """
            ).fetchall()

        return [CalendarEvent(**dict(row)) for row in rows]
