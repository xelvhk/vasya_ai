from __future__ import annotations

from core.models import IntentResult


STOP_SPEAKING_PHRASES = (
    "замолчи",
    "хватит говорить",
    "останови озвучивание",
    "прекрати озвучивание",
    "перестань говорить",
    "стоп озвучивание",
)

EXIT_ASSISTANT_PHRASES = (
    "закройся",
    "выключись",
    "заверши работу",
    "завершить работу",
    "закрыть помощника",
    "выход",
    "выключить помощника",
    "пока",
    "до встречи",
    "до свидания",
    "спокойной ночи",
)

ENABLE_CHILD_MODE_PHRASES = (
    "включи детский режим",
    "детский режим",
    "режим для ребенка",
    "режим для детей",
)

DISABLE_CHILD_MODE_PHRASES = (
    "выключи детский режим",
    "отключи детский режим",
    "обычный режим",
    "выйди из детского режима",
)

SPEED_REPORT_PHRASES = (
    "отчет скорости",
    "отчёт скорости",
    "скорость ответа",
    "покажи скорость",
    "как быстро ты отвечаешь",
)


def detect_system_intent(user_text: str) -> IntentResult | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    if normalized in STOP_SPEAKING_PHRASES:
        return IntentResult(intent="stop_speaking", data={})

    if normalized in ENABLE_CHILD_MODE_PHRASES:
        return IntentResult(intent="enable_child_mode", data={})

    if normalized in DISABLE_CHILD_MODE_PHRASES:
        return IntentResult(intent="disable_child_mode", data={})

    if normalized in EXIT_ASSISTANT_PHRASES:
        return IntentResult(intent="exit_assistant", data={})

    if normalized in SPEED_REPORT_PHRASES:
        return IntentResult(intent="speed_report", data={})

    return None
