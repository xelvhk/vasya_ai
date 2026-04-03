from __future__ import annotations

import random
import re

from assistant.child_mode import child_mode_store
from assistant.games import game_store


WORDS_BY_LETTER = {
    "а": ["арбуз", "апельсин", "автобус"],
    "б": ["банан", "бабочка", "барабан"],
    "в": ["ворона", "волк", "велосипед"],
    "г": ["груша", "глобус", "гитара"],
    "д": ["дом", "дракон", "дерево"],
    "е": ["ежик", "елка"],
    "ж": ["жираф", "жук"],
    "з": ["заяц", "зебра"],
    "и": ["иголка", "индюк"],
    "к": ["кот", "корабль", "клубника"],
    "л": ["лимон", "лампа", "лиса"],
    "м": ["машина", "мороженое", "медведь"],
    "н": ["носорог", "нитка", "ножницы"],
    "о": ["облако", "огурец", "океан"],
    "п": ["панда", "паровоз", "пирог"],
    "р": ["ракета", "рыба", "робот"],
    "с": ["самолет", "слон", "собака"],
    "т": ["трава", "танк", "телефон"],
    "у": ["улитка", "утка"],
    "ф": ["фонарь", "фламинго"],
    "х": ["хомяк", "хлеб"],
    "ц": ["цветок", "цепочка"],
    "ч": ["чайник", "черепаха"],
    "ш": ["шарик", "шоколад"],
    "э": ["экран"],
    "ю": ["юбка", "юла"],
    "я": ["яблоко", "ящерица"],
}

RIDDLES = (
    {
        "question": "Зимой и летом одним цветом. Что это?",
        "answer": "елка",
        "hint": "Это дерево.",
    },
    {
        "question": "Сидит дед, во сто шуб одет. Кто это?",
        "answer": "лук",
        "hint": "Его часто режут на кухне.",
    },
)

ANIMAL_GAME_ITEMS = (
    {
        "animal": "кот",
        "clue": "Я домашнее животное, люблю мурлыкать и ловить мышек. Кто я?",
        "hint": "Я говорю мяу.",
    },
    {
        "animal": "слон",
        "clue": "Я очень большой, у меня есть хобот. Кто я?",
        "hint": "У меня большие уши и длинный нос.",
    },
    {
        "animal": "заяц",
        "clue": "Я люблю морковку и быстро бегаю. Кто я?",
        "hint": "У меня длинные уши.",
    },
)

REPEAT_PHRASES = (
    "Рыжий кот любит молоко",
    "Синий мячик скачет быстро",
    "Маленький ежик несет гриб",
)

GAME_STOP_PHRASES = {
    "хватит играть",
    "закончим игру",
    "выход из игры",
    "останови игру",
    "не хочу играть",
    "не хочу",
    "хватит",
}

GAME_RESTART_PHRASES = {
    "сначала",
    "начни сначала",
    "давай сначала",
    "еще раз",
    "повтори игру",
}

GAME_REPEAT_LAST_PHRASES = {
    "еще",
    "давай еще",
    "еще раз",
    "давай еще раз",
}

GAME_OTHER_PHRASES = {
    "другая игра",
    "давай другую игру",
    "давай другую",
    "сменим игру",
}

GAME_HINT_PHRASES = {
    "подсказка",
    "дай подсказку",
    "подскажи",
}

GAME_CONTINUE_PHRASES = {
    "дальше",
    "еще",
    "продолжай",
    "ищи дальше",
}


def start_game(game_name: str | None) -> str:
    normalized_game = _normalize_game_name(game_name)
    if normalized_game is None:
        last_game = game_store.get_last_game()
        if last_game:
            normalized_game = last_game
    if normalized_game == "words":
        return _start_words_game()
    if normalized_game == "hide_and_seek":
        return _start_hide_and_seek()
    if normalized_game == "riddle":
        return _start_riddle_game()
    if normalized_game == "guess_animal":
        return _start_guess_animal_game()
    if normalized_game == "repeat_after_me":
        return _start_repeat_after_me_game()
    return (
        "Можем поиграть в слова, в прятки, в загадки, в угадай животное "
        "или в повтори за мной. "
        "Скажи, например: давай играть в слова."
    )


def handle_active_game_turn(user_text: str) -> str | None:
    active_game = game_store.get()
    if active_game is None:
        return None

    normalized = _normalize_text(user_text)
    if normalized in GAME_STOP_PHRASES:
        game_store.clear()
        return "Хорошо, заканчиваем игру."

    if normalized in GAME_OTHER_PHRASES:
        game_store.clear()
        return (
            "Хорошо. Давай другую игру. "
            "Можем сыграть в слова, загадки, угадай животное, прятки или повтори за мной."
        )

    if normalized in GAME_RESTART_PHRASES:
        game_store.clear()
        return start_game(active_game.game)

    if normalized in GAME_HINT_PHRASES:
        return _handle_game_hint(active_game.game, active_game.state)

    if active_game.game == "words":
        return _handle_words_turn(user_text, active_game.state)
    if active_game.game == "hide_and_seek":
        return _handle_hide_and_seek_turn(normalized)
    if active_game.game == "riddle":
        return _handle_riddle_turn(normalized, active_game.state)
    if active_game.game == "guess_animal":
        return _handle_guess_animal_turn(normalized, active_game.state)
    if active_game.game == "repeat_after_me":
        return _handle_repeat_after_me_turn(normalized, active_game.state)
    return None


def has_active_game() -> bool:
    return game_store.get() is not None


def repeat_last_game() -> str:
    last_game = game_store.get_last_game()
    if not last_game:
        return (
            "Мы еще ни во что не играли. "
            "Можем начать со слов, загадок, пряток, угадай животное или повтори за мной."
        )
    return start_game(last_game)


def is_active_game_fast_phrase(user_text: str) -> bool:
    active_game = game_store.get()
    if active_game is None:
        return False

    normalized = _normalize_text(user_text)
    if not normalized:
        return False

    if normalized in GAME_STOP_PHRASES:
        return True
    if normalized in GAME_OTHER_PHRASES:
        return True
    if normalized in GAME_RESTART_PHRASES:
        return True
    if normalized in GAME_HINT_PHRASES:
        return True
    if active_game.game == "hide_and_seek" and (
        "ищи" in normalized or normalized in GAME_CONTINUE_PHRASES
    ):
        return True
    return False


def _start_words_game() -> str:
    first_word = "кот"
    last_letter = _last_playable_letter(first_word)
    game_store.set(
        "words",
        {
            "used_words": [first_word],
            "expected_letter": last_letter,
        },
    )
    return (
        f"Давай играть в слова. Я начну: {first_word}. "
        f"Теперь твое слово на букву {last_letter}."
    )


def _handle_words_turn(user_text: str, state: dict) -> str:
    word = _extract_word(user_text)
    if not word:
        return _game_retry_reply(
            "Я не расслышал слово. Скажи одно слово для игры.",
            game_name="words",
        )

    expected_letter = state.get("expected_letter", "")
    used_words = set(state.get("used_words", []))
    if expected_letter and not word.startswith(expected_letter):
        return _game_retry_reply(
            f"Нужно слово на букву {expected_letter}. Попробуй еще раз.",
            game_name="words",
        )

    if word in used_words:
        return _game_retry_reply(
            "Такое слово уже было. Давай другое.",
            game_name="words",
        )

    used_words.add(word)
    answer_letter = _last_playable_letter(word)
    assistant_word = _choose_word(answer_letter, used_words)
    if assistant_word is None:
        state["used_words"] = list(used_words)
        state["expected_letter"] = answer_letter
        game_store.set("words", state)
        return (
            f"{_game_praise('words', strong=True)} {word} — отличное слово. "
            f"У меня пока нет ответа на букву {answer_letter}. "
            f"Ты победил! Можем сыграть еще раз."
        )

    used_words.add(assistant_word)
    next_letter = _last_playable_letter(assistant_word)
    game_store.set(
        "words",
        {
            "used_words": list(used_words),
            "expected_letter": next_letter,
        },
    )
    return (
        f"{_game_praise('words')} Мое слово: {assistant_word}. "
        f"Теперь твоя очередь, слово на букву {next_letter}."
    )


def _start_hide_and_seek() -> str:
    game_store.set("hide_and_seek", {})
    return (
        "Давай играть в прятки. Я считаю: один, два, три, четыре, пять, "
        "шесть, семь, восемь, девять, десять. Я иду искать! "
        "Скажи: нашел, если игра закончилась, или ищи дальше."
    )


def _handle_hide_and_seek_turn(normalized: str) -> str:
    if "нашел" in normalized or "нашла" in normalized:
        game_store.clear()
        return (
            f"{_game_praise('hide_and_seek', strong=True)} Ура, нашел! "
            "Было весело. Если хочешь, можем сыграть еще."
        )
    if "ищи" in normalized or normalized in GAME_CONTINUE_PHRASES:
        if child_mode_store.is_enabled():
            return random.choice(
                (
                    "Ищу, ищу. Кажется, ты спрятался очень здорово.",
                    "Ищу дальше. Наверное, ты выбрал отличное место.",
                    "Ищу. Похоже, ты умеешь хорошо прятаться.",
                )
            )
        return "Ищу, ищу. Может быть, ты спрятался очень хорошо?"
    return _game_retry_reply(
        "В прятках можно сказать: ищи дальше или нашел.",
        game_name="hide_and_seek",
    )


def _handle_game_hint(game_name: str, state: dict) -> str:
    if game_name == "words":
        expected_letter = state.get("expected_letter", "")
        if expected_letter:
            return f"Подсказка: сейчас нужно слово на букву {expected_letter}."
        return "Подсказка: скажи любое простое слово."

    if game_name == "hide_and_seek":
        return "Подсказка: в прятках можно сказать ищи дальше или нашел."

    if game_name == "riddle":
        hint = state.get("hint", "Подумай еще немного.")
        return f"Подсказка: {hint}"

    if game_name == "guess_animal":
        hint = state.get("hint", "Подумай еще немного.")
        return f"Подсказка: {hint}"

    if game_name == "repeat_after_me":
        phrase = state.get("phrase", "")
        if phrase:
            return f"Подсказка: повтори так: {phrase}"
        return "Подсказка: я скажу новую фразу, если начнем сначала."

    return "Подсказка пока не готова для этой игры."


def _start_riddle_game() -> str:
    riddle = random.choice(RIDDLES)
    game_store.set("riddle", riddle)
    return f"Загадка. {riddle['question']}"


def _handle_riddle_turn(normalized: str, state: dict) -> str:
    answer = state.get("answer", "")
    if answer and answer in normalized:
        game_store.clear()
        return f"{_game_praise('riddle', strong=True)} Правильно! Хочешь еще загадку?"
    hint = state.get("hint", "Подумай еще немного.")
    return _game_retry_reply(
        f"Пока не угадал. Подсказка: {hint}",
        game_name="riddle",
    )


def _start_guess_animal_game() -> str:
    item = random.choice(ANIMAL_GAME_ITEMS)
    game_store.set("guess_animal", item)
    return f"Угадай животное. {item['clue']}"


def _handle_guess_animal_turn(normalized: str, state: dict) -> str:
    animal = state.get("animal", "")
    if animal and animal in normalized:
        game_store.clear()
        return (
            f"{_game_praise('guess_animal', strong=True)} "
            f"Да, это {animal}! Хочешь еще одну игру?"
        )
    hint = state.get("hint", "Подумай еще немного.")
    return _game_retry_reply(
        f"Пока не угадал. Подсказка: {hint}",
        game_name="guess_animal",
    )


def _start_repeat_after_me_game() -> str:
    phrase = random.choice(REPEAT_PHRASES)
    game_store.set("repeat_after_me", {"phrase": phrase})
    return f"Повтори за мной: {phrase}"


def _handle_repeat_after_me_turn(normalized: str, state: dict) -> str:
    phrase = _normalize_text(state.get("phrase", ""))
    if not phrase:
        game_store.clear()
        return "Кажется, фраза потерялась. Давай начнем игру заново."
    if normalized == phrase:
        game_store.clear()
        return (
            f"{_game_praise('repeat_after_me', strong=True)} "
            "Ты повторил правильно! Хочешь еще?"
        )
    return _game_retry_reply(
        f"Почти. Попробуй еще раз: {state.get('phrase', '')}",
        game_name="repeat_after_me",
    )


def _normalize_game_name(game_name: str | None) -> str | None:
    normalized = _normalize_text(game_name or "")
    if normalized in {
        "words",
        "hide_and_seek",
        "riddle",
        "guess_animal",
        "repeat_after_me",
    }:
        return normalized
    if "слов" in normalized:
        return "words"
    if "прятк" in normalized:
        return "hide_and_seek"
    if "загад" in normalized:
        return "riddle"
    if "живот" in normalized or "угадай кто" in normalized:
        return "guess_animal"
    if "повтори" in normalized:
        return "repeat_after_me"
    return None


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().replace("ё", "е").split())


def _extract_word(text: str) -> str | None:
    match = re.search(r"[а-яa-z]+", _normalize_text(text))
    return match.group(0) if match else None


def _last_playable_letter(word: str) -> str:
    for letter in reversed(word):
        if letter not in {"ь", "ъ", "ы", "й"}:
            return letter
    return word[-1]


def _choose_word(letter: str, used_words: set[str]) -> str | None:
    for word in WORDS_BY_LETTER.get(letter, []):
        if word not in used_words:
            return word
    return None


def _game_praise(game_name: str | None = None, *, strong: bool = False) -> str:
    active_game = game_store.get()
    key = game_name or (active_game.game if active_game is not None else "game")

    if child_mode_store.is_enabled():
        praise_map = {
            "words": (
                "Молодец.",
                "Здорово придумал.",
                "Какое хорошее слово.",
                "Отлично получается.",
            ),
            "hide_and_seek": (
                "Ух ты, здорово.",
                "Вот это да, ты справился.",
                "Отлично получилось.",
            ),
            "riddle": (
                "Молодец.",
                "Точно, ты угадал.",
                "Здорово, правильный ответ.",
            ),
            "guess_animal": (
                "Да, молодец.",
                "Здорово, ты угадал.",
                "Отлично, верно.",
            ),
            "repeat_after_me": (
                "Здорово получилось.",
                "Отлично повторил.",
                "Молодец, очень хорошо.",
            ),
        }
        strong_map = {
            "words": (
                "Вот это да, здорово.",
                "Супер, ты отлично играешь.",
                "Ух ты, как здорово получилось.",
            ),
            "hide_and_seek": (
                "Ура, молодец.",
                "Здорово, ты справился.",
                "Вот это да, отлично вышло.",
            ),
            "riddle": (
                "Ура, молодец.",
                "Здорово, ты разгадал.",
                "Вот это да, правильный ответ.",
            ),
            "guess_animal": (
                "Ура, молодец.",
                "Здорово, ты угадал.",
                "Отлично, ты справился.",
            ),
            "repeat_after_me": (
                "Супер, получилось.",
                "Здорово, ты справился.",
                "Вот это да, отлично повторил.",
            ),
        }
        choices = strong_map.get(key) if strong else praise_map.get(key)
        choices = choices or (
            "Молодец.",
            "Здорово получается.",
            "У тебя хорошо выходит.",
            "Вот это да, отлично.",
        )
    else:
        choices = (
            "Отлично.",
            "Здорово.",
            "Хорошо получается.",
        )

    return choices[abs(hash((key, strong, len(choices)))) % len(choices)]


def _game_retry_reply(message: str, *, game_name: str | None = None) -> str:
    if not child_mode_store.is_enabled():
        return message

    active_game = game_store.get()
    key = game_name or (active_game.game if active_game is not None else "game")

    prefix_map = {
        "words": (
            "Ничего страшного.",
            "Давай еще слово.",
            "Спокойно, попробуем снова.",
        ),
        "hide_and_seek": (
            "Ничего, продолжаем.",
            "Все хорошо, играем дальше.",
            "Давай еще чуть-чуть поиграем.",
        ),
        "riddle": (
            "Ничего страшного.",
            "Почти получилось.",
            "Давай подумаем еще немного.",
        ),
        "guess_animal": (
            "Ничего страшного.",
            "Почти угадал.",
            "Давай попробуем еще раз.",
        ),
        "repeat_after_me": (
            "Ничего страшного.",
            "Почти получилось.",
            "Давай еще раз, без спешки.",
        ),
    }
    prefixes = prefix_map.get(key) or (
        "Ничего страшного.",
        "Это нормально.",
        "Давай еще раз.",
        "Спокойно, попробуем снова.",
    )
    prefix = prefixes[abs(hash((key, message))) % len(prefixes)]
    return f"{prefix} {message}"
