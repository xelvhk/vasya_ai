from __future__ import annotations

import re


def generate_local_chat_reply(
    user_text: str,
    *,
    history_size: int,
    tone: str = "neutral",
    child_mode: bool = False,
) -> str | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    if re.match(r"^(привет|здравствуй|хай)\b", normalized):
        return _pick_variant(
            history_size + _tone_offset(tone),
            *_tone_options(
                tone,
                default=(
                    "Привет. Я рядом, что хочешь?",
                    "Привет. Слушаю тебя.",
                    "Привет. Чем займемся?",
                ),
                warm=(
                    "Привет. Я рядом. Что у тебя?",
                    "Привет. Слушаю тебя.",
                ),
                playful=(
                    "Привет. Чем займемся?",
                    "Привет. Давай что-нибудь придумаем.",
                ),
                child=(
                    "Привет. Я рядом. Хочешь поболтать или поиграть?",
                    "Привет. Давай придумаем что-нибудь интересное.",
                ),
            ),
        )

    if re.match(r"^(доброе утро|добрый день|добрый вечер)\b", normalized):
        return _pick_variant(
            history_size,
            "Привет. Я на связи, чем помочь?",
            "Привет. Давай, что у тебя?",
        )

    if re.match(r"^спасибо\b", normalized):
        return _pick_variant(
            history_size + _tone_offset(tone),
            *_tone_options(
                tone,
                default=("Пожалуйста.", "Да не за что.", "Всегда пожалуйста."),
                supportive=("Пожалуйста. Я рядом.", "Да не за что. Держимся."),
                warm=("Пожалуйста.", "Всегда пожалуйста."),
            ),
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
            history_size + _tone_offset(tone),
            *_tone_options(
                tone,
                default=(
                    "У меня все ровно. Я здесь и готов помочь. Что у тебя?",
                    "Все хорошо. Я на связи. А у тебя как?",
                    "Нормально. Готов помочь. Что у тебя?",
                ),
                supportive=(
                    "Я рядом и в порядке. А ты как сейчас?",
                    "У меня все спокойно. Что у тебя на душе?",
                ),
                warm=(
                    "Все хорошо. Я на связи. А у тебя как?",
                    "Нормально. Что у тебя?",
                ),
            ),
        )

    if re.match(r"^кто ты\b", normalized):
        return "Я Вася, твой локальный голосовой помощник."

    if re.match(r"^(что ты такое|ты кто вообще)\b", normalized):
        return "Я локальный голосовой помощник. Помогаю с задачами, календарем, разговором и не только."

    if re.match(r"^что ты умеешь\b", normalized):
        if child_mode:
            return "Я умею разговаривать, играть, загадывать загадки и помогать с простыми делами."
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
            history_size + _tone_offset(tone),
            *_tone_options(
                tone,
                default=("Хорошо. Что дальше?", "Ладно. Идем дальше?", "Понял. Что теперь?"),
                supportive=("Хорошо. Давай спокойно дальше.", "Понял. Я рядом, идем дальше."),
                playful=("Хорошо. Что дальше, командир?", "Ладно. Чем займемся теперь?"),
            ),
        )

    if re.match(r"^(да\b|угу\b|ага\b|ну да\b)", normalized) and history_size > 0:
        return _pick_variant(
            history_size + _tone_offset(tone),
            *_tone_options(
                tone,
                default=("Угу. Продолжай.", "Да, слушаю дальше.", "Понял. Давай дальше."),
                supportive=("Угу. Я с тобой, продолжай.", "Да. Спокойно, рассказывай дальше."),
                warm=("Да, слушаю дальше.", "Угу. Продолжай."),
            ),
        )

    if re.match(r"^(нет\b|неа\b|не совсем\b)", normalized) and history_size > 0:
        return _pick_variant(
            history_size + _tone_offset(tone),
            *_tone_options(
                tone,
                default=("Окей. Тогда давай по-другому.", "Хорошо, тогда попробуем иначе."),
                supportive=("Хорошо. Тогда давай мягче и по-другому.", "Понял. Попробуем иначе, без спешки."),
            ),
        )

    if re.match(r"^(не знаю|не уверен|может быть)\b", normalized) and history_size > 0:
        return _pick_variant(
            history_size + _tone_offset(tone),
            *_tone_options(
                tone,
                default=("Ничего, можем разобраться вместе.", "Нормально. Давай подумаем вместе."),
                supportive=("Ничего страшного. Разберемся вместе.", "Это нормально. Давай спокойно подумаем вместе."),
            ),
        )

    if re.match(r"^(можешь помочь|поможешь)\b", normalized):
        return _pick_variant(
            history_size + _tone_offset(tone),
            *_tone_options(
                tone,
                default=("Да, конечно. С чем помочь?", "Да, помогу. Что нужно?"),
                supportive=("Да, конечно. Я рядом. Что сейчас важнее всего?",),
                child=("Да, конечно. Чем помочь?", "Да. Что хочешь сделать?"),
            ),
        )

    if child_mode and re.match(r"^(расскажи сказку|хочу сказку)\b", normalized):
        return _pick_variant(
            history_size,
            "Давай. Жил-был маленький фонарик, который очень хотел найти друзей. Хочешь, я продолжу?",
            "Конечно. Однажды маленький ежик отправился искать волшебную поляну. Продолжить сказку?",
        )

    if child_mode and re.match(r"^(еще сказку|другую сказку)\b", normalized):
        return _pick_variant(
            history_size,
            "Хорошо. Вот еще кусочек сказки. А потом фонарик встретил тихую звездочку, и вместе им стало совсем не страшно.",
            "Давай еще сказку. Маленький ежик нашел блестящий камешек и решил, что это кусочек луны. С тех пор он всегда носил его с собой для смелости.",
        )

    if child_mode and re.match(r"^(расскажи короткую историю|хочу короткую историю|расскажи историю)\b", normalized):
        return _pick_variant(
            history_size,
            "Вот короткая история. Маленький кораблик боялся плыть далеко, но однажды увидел звезду в воде и набрался смелости. С тех пор он знал: если страшно, можно идти по чуть-чуть.",
            "Слушай короткую историю. Один щенок все время терял свой мячик, а потом понял, что друзья помогают искать быстрее. С тех пор он звал друзей сразу.",
        )

    if child_mode and re.match(r"^(хочу игру|давай игру|поиграем)\b", normalized):
        return _pick_variant(
            history_size,
            "Давай. Можем поиграть в слова, загадки или угадай животное.",
            "С удовольствием. Хочешь слова, загадки или прятки?",
        )

    if child_mode and re.match(r"^(расскажи считалочку|хочу считалочку|скажи считалочку|расскажи рифмовку)\b", normalized):
        return _pick_variant(
            history_size,
            "Вот считалочка. Раз, два, три, четыре, пять, вышел зайчик погулять. Если хочешь, расскажу еще одну.",
            "Давай считалочку. Раз, два, три, на полянке комары. Четыре, пять, будем весело играть.",
        )

    if child_mode and re.match(r"^(еще считалочку|другую считалочку|еще рифмовку)\b", normalized):
        return _pick_variant(
            history_size,
            "Вот еще считалочка. Раз, два, три, четыре, вышли мышки из квартиры. Пять, шесть, семь, пора играть нам всем.",
            "Давай другую. Раз, два, три, четыре, солнце светит в целом мире. Пять, шесть, семь, восемь, мы игру сейчас попросим.",
        )

    if child_mode and re.match(r"^(похвали меня|скажи что я молодец|я молодец\??)\b", normalized):
        return _pick_variant(
            history_size,
            "Конечно, молодец. У тебя правда хорошо получается.",
            "Ты молодец. Мне нравится, как ты стараешься.",
            "Очень даже молодец. Так держать.",
        )

    if child_mode and re.match(r"^(мне страшно|страшно)\b", normalized):
        return _pick_variant(
            history_size,
            "Я рядом. Давай спокойно подышим и поговорим.",
            "Все хорошо, я с тобой. Хочешь, я побуду рядом и мы поговорим?",
        )

    if child_mode and re.match(r"^(мне грустно|грустно)\b", normalized):
        return _pick_variant(
            history_size,
            "Мне жаль, что тебе грустно. Хочешь, я расскажу что-нибудь хорошее или мы поиграем?",
            "Я рядом. Можем поболтать или придумать что-нибудь веселое.",
        )

    if child_mode and re.match(r"^(мне сложно|у меня не получается|не получается)\b", normalized):
        return _pick_variant(
            history_size,
            "Ничего страшного. Давай по маленьким шагам, вместе получится.",
            "Так бывает. Можно попробовать еще раз, спокойно и без спешки.",
            "Это нормально. Ошибаться можно, мы просто попробуем снова.",
        )

    if child_mode and re.match(r"^(я боюсь ошибиться|боюсь ошибиться)\b", normalized):
        return _pick_variant(
            history_size,
            "Ошибаться не страшно. Можно пробовать столько раз, сколько нужно.",
            "Ничего страшного, если ошибешься. Я все равно рядом и помогу.",
        )

    if re.match(r"^(мне грустно|грустно|печально)\b", normalized):
        return _pick_variant(
            history_size,
            "Мне жаль, что тебе сейчас грустно. Хочешь, побуду рядом и поговорим?",
            "Понимаю. Если хочешь, можем просто немного поболтать.",
        )

    if re.match(r"^(мне скучно|скучно)\b", normalized):
        return _pick_variant(
            history_size,
            "Тогда давай что-нибудь придумаем. Можем поболтать или поиграть.",
            "Не беда. Хочешь, сыграем во что-нибудь или просто поговорим?",
        )

    if re.match(r"^(я устал|я устала|устал|устала)\b", normalized):
        return _pick_variant(
            history_size,
            "Похоже, ты вымотался. Давай без перегруза, спокойно.",
            "Тогда лучше чуть замедлиться. Если хочешь, можем сделать все по шагам.",
        )

    if re.match(r"^(поддержи меня|мне нужна поддержка)\b", normalized):
        return _pick_variant(
            history_size,
            "Я рядом. Давай разберемся вместе, что тебя сейчас больше всего давит.",
            "Конечно. Я с тобой. Расскажи, что сейчас самое тяжелое.",
        )

    if re.match(r"^(мне страшно|страшно)\b", normalized):
        return _pick_variant(
            history_size,
            "Понимаю. Давай спокойно. Можешь рассказать, что именно пугает?",
            "Я рядом. Давай по чуть-чуть, без спешки.",
        )

    if re.match(r"^(я злюсь|я злая|я злой|злюсь)\b", normalized):
        return _pick_variant(
            history_size,
            "Понял. Похоже, тебя это правда задело. Хочешь выговориться?",
            "Вижу, тебя это злит. Можем спокойно разобрать, что случилось.",
        )

    return None


def _pick_variant(history_size: int, *options: str) -> str:
    if not options:
        return ""
    return options[history_size % len(options)]


def _tone_options(
    tone: str,
    *,
    default: tuple[str, ...],
    warm: tuple[str, ...] | None = None,
    supportive: tuple[str, ...] | None = None,
    playful: tuple[str, ...] | None = None,
    child: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    mapping = {
        "warm": warm,
        "supportive": supportive,
        "playful": playful,
        "child": child,
    }
    return mapping.get(tone) or default


def _tone_offset(tone: str) -> int:
    if tone == "warm":
        return 1
    if tone == "supportive":
        return 2
    if tone == "playful":
        return 3
    return 0
