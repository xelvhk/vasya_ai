from repositories.task_repository import TaskRepository


_task_repository = TaskRepository()


def create_task(task: str) -> dict:
    return _task_repository.create(task).model_dump()


def get_tasks() -> list:
    return [task.model_dump() for task in _task_repository.list_all()]
