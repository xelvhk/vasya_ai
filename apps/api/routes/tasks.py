from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas import CreateTaskRequest
from services.task_service import create_task, get_tasks


router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


@router.get("")
def list_tasks(date: str | None = None) -> dict:
    return {"items": get_tasks(filter_date=date)}


@router.post("")
def add_task(payload: CreateTaskRequest) -> dict:
    task = create_task(payload.task.strip(), dt=payload.datetime)
    return {"item": task}

