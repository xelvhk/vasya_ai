from assistant.child_mode import child_mode_store
from assistant.control import assistant_control
from agents.chat_agent import handle_chat_intent
from agents.game_agent import handle_game_intent
from agents.note_agent import handle_note_intent
from core.models import IntentResult
from agents.calendar_agent import handle_calendar_intent
from agents.task_agent import handle_task_intent
from voice.tts import stop_speaking

def route_intent(intent_result: IntentResult, user_text: str) -> str:
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

    if intent_result.intent in ("create_note", "get_notes", "export_notes"):
        return handle_note_intent(intent_result)

    if intent_result.intent == "play_game":
        return handle_game_intent(intent_result)

    if intent_result.intent == "stop_speaking":
        stop_speaking()
        return ""

    if intent_result.intent == "enable_child_mode":
        child_mode_store.enable()
        return (
            "Хорошо. Включил детский режим. "
            "Теперь я буду говорить проще, мягче и без взрослых тем."
        )

    if intent_result.intent == "disable_child_mode":
        child_mode_store.disable()
        return "Хорошо. Выключил детский режим."

    if intent_result.intent == "exit_assistant":
        stop_speaking()
        assistant_control.request_exit()
        return "Завершаю работу."

    if intent_result.intent in ("chat", "unknown"):
        return handle_chat_intent(user_text)

    return "Я пока не понял команду. Попробуй сказать по-другому."
