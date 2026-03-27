from repositories.task_repository import TaskRepository


_task_repository = TaskRepository()


def create_task(task: str, dt: str | None = None) -> dict:
    return _task_repository.create(task, dt=dt).model_dump()


def get_tasks(filter_date: str | None = None) -> list:
    return [task.model_dump() for task in _task_repository.list_all(filter_date=filter_date)]


def complete_task(task_id: int) -> dict | None:
    task = _task_repository.mark_completed(task_id)
    return task.model_dump() if task else None


def delete_task(task_id: int) -> bool:
    return _task_repository.delete(task_id)


def delete_tasks_by_date(filter_date: str) -> int:
    return _task_repository.delete_by_date(filter_date)


def count_open_tasks() -> int:
    return _task_repository.count_open()


def delete_all_tasks() -> int:
    return _task_repository.delete_all_open()
