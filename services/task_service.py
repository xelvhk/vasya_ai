from storage.db import current_timestamp, get_connection, initialize_database


def create_task(task: str) -> dict:
    initialize_database()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (task, status, source, external_id, created_at)
            VALUES (?, 'open', 'local', NULL, ?)
            """,
            (task, current_timestamp()),
        )
        row = connection.execute(
            "SELECT id, task, status, source, external_id, created_at FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return dict(row)


def get_tasks() -> list:
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, task, status, source, external_id, created_at
            FROM tasks
            ORDER BY id ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]
