from storage.db import current_timestamp, get_connection, initialize_database


def create_event(title: str, dt: str | None = None) -> dict:
    initialize_database()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO events (title, datetime, source, external_id, created_at)
            VALUES (?, ?, 'local', NULL, ?)
            """,
            (title, dt, current_timestamp()),
        )
        row = connection.execute(
            """
            SELECT id, title, datetime, source, external_id, created_at
            FROM events
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return dict(row)


def get_events() -> list:
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, title, datetime, source, external_id, created_at
            FROM events
            ORDER BY id ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]
