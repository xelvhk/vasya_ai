from core.models import IntentResult
from agents.calendar_agent import handle_calendar_intent
from agents.task_agent import handle_task_intent

def route_intent(intent_result: IntentResult) -> str:
    if intent_result.intent in ("create_event", "get_events", "delete_event"):
        return handle_calendar_intent(intent_result)

    if intent_result.intent in (
        "create_task",
        "get_tasks",
        "complete_task",
        "delete_task",
        "delete_tasks",
    ):
        return handle_task_intent(intent_result)

    return "Я пока не понял команду. Попробуй сказать по-другому."
