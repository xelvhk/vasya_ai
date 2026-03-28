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


def detect_system_intent(user_text: str) -> IntentResult | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    if normalized in STOP_SPEAKING_PHRASES:
        return IntentResult(intent="stop_speaking", data={})

    if normalized in EXIT_ASSISTANT_PHRASES:
        return IntentResult(intent="exit_assistant", data={})

    return None
