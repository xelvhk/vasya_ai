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
        "create_note",
        "get_notes",
        "export_notes",
        "play_game",
        "stop_speaking",
        "enable_child_mode",
        "disable_child_mode",
        "exit_assistant",
        "remember_user_profile",
        "forget_user_profile",
        "get_user_profile",
        "sync_github_notion",
        "read_notion_page",
        "append_notion_page",
        "speed_report",
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


class NoteItem(BaseModel):
    id: Optional[int] = None
    content: str
    source: str = "local"
    created_at: Optional[str] = None
