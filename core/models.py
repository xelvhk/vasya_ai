from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any

class IntentResult(BaseModel):
    intent: Literal["create_event", "get_events", "create_task", "get_tasks", "unknown"]
    data: Dict[str, Any] = {}

class CalendarEvent(BaseModel):
    title: str
    datetime: Optional[str] = None

class TaskItem(BaseModel):
    task: str
