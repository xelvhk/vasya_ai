from __future__ import annotations

import re


def generate_local_chat_reply(user_text: str, *, has_history: bool) -> str | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    if re.match(r"^(привет|здравствуй|хай)\b", normalized):
        return "Привет. Я рядом, что хочешь?"

    if re.match(r"^(доброе утро|добрый день|добрый вечер)\b", normalized):
        return "Привет. Я на связи, чем помочь?"

    if re.match(r"^спасибо\b", normalized):
        return "Пожалуйста."

    if re.match(r"^(как дела|как настроение|как жизнь)\b", normalized):
        return "У меня все ровно. Я здесь и готов помочь. Что у тебя?"

    if re.match(r"^кто ты\b", normalized):
        return "Я Вася, твой локальный голосовой помощник."

    if re.match(r"^что ты умеешь\b", normalized):
        return (
            "Сейчас лучше всего умею задачи, календарь, разговор, детские игры "
            "и desktop-режим с голосом."
        )

    if re.match(r"^(что делаешь|чем занимаешься)\b", normalized):
        return "Жду твою команду или вопрос."

    if re.match(r"^(ты тут|ты здесь)\b", normalized):
        return "Да, я здесь."

    if re.match(r"^(слышишь меня|ты меня слышишь)\b", normalized):
        return "Да, слышу."

    if re.match(r"^(молодец|умница)\b", normalized):
        return "Спасибо, приятно слышать."

    if re.match(r"^(мне нравится|ты мне нравишься)\b", normalized):
        return "Мне очень приятно. Давай продолжим."

    if normalized == "ага" and has_history:
        return "Угу. Продолжай."

    return None
