from core.models import TaskItem
from storage.db import current_timestamp, get_connection, initialize_database


class TaskRepository:
    def create(self, task_text: str, source: str = "local") -> TaskItem:
        initialize_database()

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (task, status, source, external_id, created_at)
                VALUES (?, 'open', ?, NULL, ?)
                """,
                (task_text, source, current_timestamp()),
            )
            row = connection.execute(
                """
                SELECT id, task, status, source, external_id, created_at
                FROM tasks
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

        return TaskItem(**dict(row))

    def list_all(self) -> list[TaskItem]:
        initialize_database()

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, task, status, source, external_id, created_at
                FROM tasks
                ORDER BY id ASC
                """
            ).fetchall()

        return [TaskItem(**dict(row)) for row in rows]
