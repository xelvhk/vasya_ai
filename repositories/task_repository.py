from core.models import TaskItem
from storage.db import current_timestamp, get_connection, initialize_database


class TaskRepository:
    def create(
        self,
        task_text: str,
        dt: str | None = None,
        source: str = "local",
    ) -> TaskItem:
        initialize_database()

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (task, datetime, status, source, external_id, created_at)
                VALUES (?, ?, 'open', ?, NULL, ?)
                """,
                (task_text, dt, source, current_timestamp()),
            )
            row = connection.execute(
                """
                SELECT id, task, datetime, status, source, external_id, created_at
                FROM tasks
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

        return TaskItem(**dict(row))

    def list_all(self, filter_date: str | None = None) -> list[TaskItem]:
        initialize_database()

        with get_connection() as connection:
            if filter_date:
                rows = connection.execute(
                    """
                    SELECT id, task, datetime, status, source, external_id, created_at
                    FROM tasks
                    WHERE status = 'open' AND datetime LIKE ?
                    ORDER BY datetime ASC, id DESC
                    """,
                    (f"{filter_date}%",),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id, task, datetime, status, source, external_id, created_at
                    FROM tasks
                    WHERE status = 'open'
                    ORDER BY datetime IS NULL, datetime ASC, id DESC
                    """
                ).fetchall()

        return [TaskItem(**dict(row)) for row in rows]

    def mark_completed(self, task_id: int) -> TaskItem | None:
        initialize_database()

        with get_connection() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET status = 'done'
                WHERE id = ?
                """,
                (task_id,),
            )
            row = connection.execute(
                """
                SELECT id, task, datetime, status, source, external_id, created_at
                FROM tasks
                WHERE id = ?
                """,
                (task_id,),
            ).fetchone()

        return TaskItem(**dict(row)) if row else None

    def delete(self, task_id: int) -> bool:
        initialize_database()

        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        return cursor.rowcount > 0

    def delete_by_date(self, filter_date: str) -> int:
        initialize_database()

        with get_connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM tasks
                WHERE status = 'open' AND datetime LIKE ?
                """,
                (f"{filter_date}%",),
            )

        return cursor.rowcount

    def count_open(self) -> int:
        initialize_database()

        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS task_count
                FROM tasks
                WHERE status = 'open'
                """
            ).fetchone()

        return int(row["task_count"]) if row else 0

    def delete_all_open(self) -> int:
        initialize_database()

        with get_connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM tasks
                WHERE status = 'open'
                """
            )

        return cursor.rowcount
