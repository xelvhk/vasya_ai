from __future__ import annotations

from config.settings import TASKS_BACKEND
from services.obsidian_daily_tasks_service import (
    complete_task_in_daily_notes,
    count_open_tasks_in_daily_notes,
    create_task_in_daily_note,
    delete_all_open_tasks_in_daily_notes,
    delete_task_from_daily_notes,
    list_tasks_from_daily_notes,
)
from services.task_service import (
    complete_task as complete_task_legacy,
    count_open_tasks as count_open_tasks_legacy,
    create_task as create_task_legacy,
    delete_all_tasks as delete_all_tasks_legacy,
    delete_task as delete_task_legacy,
    delete_tasks_by_date as delete_tasks_by_date_legacy,
    get_tasks as get_tasks_legacy,
)


def create_task(task: str, dt: str | None = None) -> dict:
    if _use_obsidian_daily():
        return create_task_in_daily_note(task, dt=dt)
    return create_task_legacy(task, dt=dt)


def get_tasks(filter_date: str | None = None) -> list[dict]:
    if _use_obsidian_daily():
        return list_tasks_from_daily_notes(filter_date=filter_date)
    return get_tasks_legacy(filter_date=filter_date)


def complete_task(task_id_or_target) -> dict | None:
    if _use_obsidian_daily():
        return complete_task_in_daily_notes(target=str(task_id_or_target))
    try:
        task_id = int(task_id_or_target)
    except (TypeError, ValueError):
        return None
    return complete_task_legacy(task_id)


def delete_task(task_id_or_target) -> bool:
    if _use_obsidian_daily():
        return delete_task_from_daily_notes(target=str(task_id_or_target))
    try:
        task_id = int(task_id_or_target)
    except (TypeError, ValueError):
        return False
    return delete_task_legacy(task_id)


def delete_tasks_by_date(filter_date: str) -> int:
    if _use_obsidian_daily():
        return delete_all_open_tasks_in_daily_notes(filter_date=filter_date)
    return delete_tasks_by_date_legacy(filter_date)


def count_open_tasks() -> int:
    if _use_obsidian_daily():
        return count_open_tasks_in_daily_notes()
    return count_open_tasks_legacy()


def delete_all_tasks() -> int:
    if _use_obsidian_daily():
        return delete_all_open_tasks_in_daily_notes()
    return delete_all_tasks_legacy()


def _use_obsidian_daily() -> bool:
    return TASKS_BACKEND == "obsidian_daily"
