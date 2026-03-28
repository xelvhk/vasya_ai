from __future__ import annotations

import re


def generate_local_chat_reply(user_text: str, *, history_size: int) -> str | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    if re.match(r"^(привет|здравствуй|хай)\b", normalized):
        return _pick_variant(
            history_size,
            "Привет. Я рядом, что хочешь?",
            "Привет. Слушаю тебя.",
            "Привет. Чем займемся?",
        )

    if re.match(r"^(доброе утро|добрый день|добрый вечер)\b", normalized):
        return _pick_variant(
            history_size,
            "Привет. Я на связи, чем помочь?",
            "Привет. Давай, что у тебя?",
        )

    if re.match(r"^спасибо\b", normalized):
        return _pick_variant(
            history_size,
            "Пожалуйста.",
            "Да не за что.",
            "Всегда пожалуйста.",
        )

    if re.match(r"^(как тебя зовут|тебя как зовут|как зовут тебя)\b", normalized):
        return _pick_variant(
            history_size,
            "Меня зовут Вася.",
            "Я Вася.",
        )

    if re.match(r"^(ты вася|тебя зовут вася)\b", normalized):
        return "Да, я Вася."

    if re.match(r"^(почему ты вася|почему тебя зовут вася)\b", normalized):
        return "Потому что Вася это Voice AI Assistant. Коротко и легко запомнить."

    if re.match(r"^(как дела|как настроение|как жизнь)\b", normalized):
        return _pick_variant(
            history_size,
            "У меня все ровно. Я здесь и готов помочь. Что у тебя?",
            "Все хорошо. Я на связи. А у тебя как?",
            "Нормально. Готов помочь. Что у тебя?",
        )

    if re.match(r"^кто ты\b", normalized):
        return "Я Вася, твой локальный голосовой помощник."

    if re.match(r"^(что ты такое|ты кто вообще)\b", normalized):
        return "Я локальный голосовой помощник. Помогаю с задачами, календарем, разговором и не только."

    if re.match(r"^что ты умеешь\b", normalized):
        return (
            "Сейчас лучше всего умею задачи, календарь, разговор, детские игры "
            "и desktop-режим с голосом."
        )

    if re.match(r"^(что нового|как ты)\b", normalized):
        return _pick_variant(
            history_size,
            "Я в порядке и готов помогать. С чем пойдем дальше?",
            "Все нормально. Давай, что у тебя?",
        )

    if re.match(r"^(что делаешь|чем занимаешься)\b", normalized):
        return _pick_variant(
            history_size,
            "Жду твою команду или вопрос.",
            "Слушаю тебя.",
        )

    if re.match(r"^(ты тут|ты здесь)\b", normalized):
        return "Да, я здесь."

    if re.match(r"^(слышишь меня|ты меня слышишь)\b", normalized):
        return "Да, слышу."

    if re.match(r"^(молодец|умница)\b", normalized):
        return _pick_variant(
            history_size,
            "Спасибо, приятно слышать.",
            "Спасибо. Это приятно.",
        )

    if re.match(r"^(мне нравится|ты мне нравишься)\b", normalized):
        return "Мне очень приятно. Давай продолжим."

    if re.match(r"^(хорошо|ладно|понятно|ясно)\b", normalized) and history_size > 0:
        return _pick_variant(
            history_size,
            "Хорошо. Что дальше?",
            "Ладно. Идем дальше?",
            "Понял. Что теперь?",
        )

    if re.match(r"^(да\b|угу\b|ага\b|ну да\b)", normalized) and history_size > 0:
        return _pick_variant(
            history_size,
            "Угу. Продолжай.",
            "Да, слушаю дальше.",
            "Понял. Давай дальше.",
        )

    if re.match(r"^(нет\b|неа\b|не совсем\b)", normalized) and history_size > 0:
        return _pick_variant(
            history_size,
            "Окей. Тогда давай по-другому.",
            "Хорошо, тогда попробуем иначе.",
        )

    if re.match(r"^(не знаю|не уверен|может быть)\b", normalized) and history_size > 0:
        return _pick_variant(
            history_size,
            "Ничего, можем разобраться вместе.",
            "Нормально. Давай подумаем вместе.",
        )

    if re.match(r"^(можешь помочь|поможешь)\b", normalized):
        return _pick_variant(
            history_size,
            "Да, конечно. С чем помочь?",
            "Да, помогу. Что нужно?",
        )

    return None


def _pick_variant(history_size: int, *options: str) -> str:
    if not options:
        return ""
    return options[history_size % len(options)]
