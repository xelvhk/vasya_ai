from agents.chat_agent import handle_chat_intent
from core.agent_policy import role_for_intent
from core.models import IntentResult
from core.tools import dispatch_tool


_COMMAND_HINT_MARKERS = (
    "задач",
    "задачу",
    "дела",
    "событ",
    "календар",
    "встреч",
    "добавь",
    "создай",
    "удали",
    "покажи",
    "запомни",
    "забуд",
    "обо мне",
    "про меня",
    "notion",
    "ноушн",
    "github",
    "гитхаб",
    "заметк",
    "выгрузи",
    "экспорт",
    "игр",
    "обсидиан",
    "браузер",
    "сайт",
    "ссылк",
    "введи",
    "нажми",
    "клик",
    "прокрут",
    "скрол",
)

def route_intent(intent_result: IntentResult, user_text: str) -> str:
    role = role_for_intent(intent_result.intent)
    tool_response = dispatch_tool(intent_result)
    if tool_response is not None:
        return tool_response

    if intent_result.intent == "unknown":
        command_clarification = _clarify_unknown_command(user_text)
        if command_clarification is not None:
            return command_clarification
        return handle_chat_intent(user_text)

    if intent_result.intent == "chat" or role == "chat_agent":
        return handle_chat_intent(user_text)

    return "Я пока не понял команду. Попробуй сказать по-другому."


def _clarify_unknown_command(user_text: str) -> str | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    clearly_conversational_starts = (
        "привет",
        "здравствуй",
        "как дела",
        "как настроение",
        "как жизнь",
        "как ты",
        "что нового",
        "кто ты",
        "можешь помочь",
        "поможешь",
        "спасибо",
    )
    if normalized.startswith(clearly_conversational_starts):
        return None

    if "?" in normalized and not any(marker in normalized for marker in _COMMAND_HINT_MARKERS):
        return None

    if any(marker in normalized for marker in _COMMAND_HINT_MARKERS):
        return (
            "Не до конца поняла, что именно нужно сделать. "
            "Можешь сказать короче, например: покажи задачи, добавь событие или запомни заметку?"
        )

    short_imperative_starts = (
        "добавь",
        "создай",
        "покажи",
        "удали",
        "запомни",
        "выгрузи",
        "экспортируй",
        "отметь",
    )
    if normalized.startswith(short_imperative_starts):
        return (
            "Я услышала команду, но не до конца поняла детали. "
            "Повтори чуть точнее, пожалуйста."
        )

    return None
