from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel


class IntentResult(BaseModel):
    intent: Literal[
        "create_event",
        "get_events",
        "delete_event",
        "create_task",
        "get_tasks",
        "complete_task",
        "delete_task",
        "delete_tasks",
        "stop_speaking",
        "exit_assistant",
        "chat",
        "unknown",
    ]
    data: Dict[str, Any] = {}


class CalendarEvent(BaseModel):
    id: Optional[int] = None
    title: str
    datetime: Optional[str] = None
    source: str = "local"
    external_id: Optional[str] = None
    created_at: Optional[str] = None


class TaskItem(BaseModel):
    id: Optional[int] = None
    task: str
    datetime: Optional[str] = None
    status: str = "open"
    source: str = "local"
    external_id: Optional[str] = None
    created_at: Optional[str] = None
