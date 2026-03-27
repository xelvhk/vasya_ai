from __future__ import annotations

import re

from core.models import IntentResult


_COMMAND_MARKERS = (
    "задач",
    "задачу",
    "задача",
    "дела на",
    "событ",
    "календар",
    "встреч",
    "созвон",
    "напом",
    "добавь",
    "создай",
    "удали",
    "покажи",
    "список",
    "отметь",
    "выполн",
    "сегодня",
    "завтра",
    "послезавтра",
    "через ",
)

_CHAT_PATTERNS = (
    r"^привет\b",
    r"^здравствуй\b",
    r"^доброе утро\b",
    r"^добрый день\b",
    r"^добрый вечер\b",
    r"^как дела\b",
    r"^как настроение\b",
    r"^как жизнь\b",
    r"^кто ты\b",
    r"^что ты умеешь\b",
    r"^что делаешь\b",
    r"^чем занимаешься\b",
    r"^спасибо\b",
    r"^мне нравится\b",
    r"^ты мне нравишься\b",
    r"^у тебя\b",
    r"^а у меня\b",
    r"^я думаю\b",
    r"^мне кажется\b",
)


def detect_fast_intent(user_text: str) -> IntentResult | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    if any(marker in normalized for marker in _COMMAND_MARKERS):
        return None

    if normalized.endswith("?"):
        return IntentResult(intent="chat", data={})

    if any(re.search(pattern, normalized) for pattern in _CHAT_PATTERNS):
        return IntentResult(intent="chat", data={})

    return None
