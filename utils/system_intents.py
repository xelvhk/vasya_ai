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
    "диагностика скорости",
    "покажи диагностику скорости",
    "дай диагностику скорости",
    "скорость ответа",
    "покажи скорость",
    "как быстро ты отвечаешь",
)

OPEN_TEXT_COMMAND_PHRASES = (
    "открой текстовое окно",
    "открой текстовую команду",
    "открой окно ввода",
    "открой текстовый ввод",
    "покажи текстовое окно",
    "покажи окно ввода",
    "переключись в текстовый режим",
    "текстовый режим",
)

MIC_TEST_PHRASES = (
    "проверь микрофон",
    "тест микрофона",
    "проверь мой микрофон",
    "сделай тест микрофона",
)

AUTO_TUNE_VOICE_PHRASES = (
    "подбери настройки голоса",
    "подбери настройки голоса автоматически",
    "авто тюнинг голоса",
    "автотюнинг голоса",
    "настрой голос автоматически",
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

    if normalized in OPEN_TEXT_COMMAND_PHRASES:
        return IntentResult(intent="open_text_command", data={})

    if normalized in MIC_TEST_PHRASES:
        return IntentResult(intent="mic_test", data={})

    if normalized in AUTO_TUNE_VOICE_PHRASES:
        return IntentResult(intent="auto_tune_voice", data={})

    return None
