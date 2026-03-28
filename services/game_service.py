from __future__ import annotations

import random
import re

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
}


def start_game(game_name: str | None) -> str:
    normalized_game = _normalize_game_name(game_name)
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
        return "Я не расслышал слово. Скажи одно слово для игры."

    expected_letter = state.get("expected_letter", "")
    used_words = set(state.get("used_words", []))
    if expected_letter and not word.startswith(expected_letter):
        return f"Нужно слово на букву {expected_letter}. Попробуй еще раз."

    if word in used_words:
        return "Такое слово уже было. Давай другое."

    used_words.add(word)
    answer_letter = _last_playable_letter(word)
    assistant_word = _choose_word(answer_letter, used_words)
    if assistant_word is None:
        state["used_words"] = list(used_words)
        state["expected_letter"] = answer_letter
        game_store.set("words", state)
        return (
            f"Хорошее слово: {word}. У меня пока нет ответа на букву {answer_letter}. "
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
        f"Мое слово: {assistant_word}. "
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
        return "Ура, нашел! Было весело. Если хочешь, можем сыграть еще."
    if "ищи" in normalized:
        return "Ищу, ищу. Может быть, ты спрятался очень хорошо?"
    return "В прятках можно сказать: ищи дальше или нашел."


def _start_riddle_game() -> str:
    riddle = random.choice(RIDDLES)
    game_store.set("riddle", riddle)
    return f"Загадка. {riddle['question']}"


def _handle_riddle_turn(normalized: str, state: dict) -> str:
    answer = state.get("answer", "")
    if answer and answer in normalized:
        game_store.clear()
        return "Правильно! Молодец. Хочешь еще загадку?"
    hint = state.get("hint", "Подумай еще немного.")
    return f"Пока не угадал. Подсказка: {hint}"


def _start_guess_animal_game() -> str:
    item = random.choice(ANIMAL_GAME_ITEMS)
    game_store.set("guess_animal", item)
    return f"Угадай животное. {item['clue']}"


def _handle_guess_animal_turn(normalized: str, state: dict) -> str:
    animal = state.get("animal", "")
    if animal and animal in normalized:
        game_store.clear()
        return f"Да, это {animal}! Здорово, ты угадал. Хочешь еще одну игру?"
    hint = state.get("hint", "Подумай еще немного.")
    return f"Пока не угадал. Подсказка: {hint}"


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
        return "Отлично, ты повторил правильно! Хочешь еще?"
    return f"Почти. Попробуй еще раз: {state.get('phrase', '')}"


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
