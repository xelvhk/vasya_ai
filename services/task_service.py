import json
import os
from config.settings import TASK_STORAGE_FILE

def _load_tasks() -> list:
    if not os.path.exists(TASK_STORAGE_FILE):
        return []

    with open(TASK_STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_tasks(tasks: list) -> None:
    with open(TASK_STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def create_task(task: str) -> dict:
    tasks = _load_tasks()
    item = {"task": task}
    tasks.append(item)
    _save_tasks(tasks)
    return item

def get_tasks() -> list:
    return _load_tasks()