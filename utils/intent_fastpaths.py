from __future__ import annotations

import re

from core.models import IntentResult
from utils.system_intents import detect_system_intent


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
    "запомни",
    "заметк",
    "помнишь",
    "обо мне",
    "про меня",
    "забуд",
    "личную память",
    "личная память",
    "notion",
    "ноушн",
    "гитхаб",
    "github",
    "репозитори",
    "браузер",
    "сайт",
    "ссылк",
    "окно",
    "введи",
    "вставь",
    "диктуй",
    "продиктуй",
    "нажми",
    "клик",
    "прокрут",
    "скрол",
    "приложени",
    "обсидиан",
    "выгрузи",
    "экспорт",
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
    r"^ку\b",
    r"^хей\b",
    r"^хэй\b",
    r"^здравствуй\b",
    r"^доброе утро\b",
    r"^добрый день\b",
    r"^добрый вечер\b",
    r"^как тебя зовут\b",
    r"^тебя как зовут\b",
    r"^как зовут тебя\b",
    r"^ты вася\b",
    r"^почему ты вася\b",
    r"^почему тебя зовут вася\b",
    r"^как дела\b",
    r"^как настроение\b",
    r"^как жизнь\b",
    r"^как ты\b",
    r"^что нового\b",
    r"^кто ты\b",
    r"^что ты такое\b",
    r"^что ты умеешь\b",
    r"^что делаешь\b",
    r"^чем занимаешься\b",
    r"^(пошути|рассмеши меня|скажи шутку|скажи каламбур|каламбур)\b",
    r"^можешь помочь\b",
    r"^поможешь\b",
    r"^спасибо\b",
    r"^мне нравится\b",
    r"^ты мне нравишься\b",
    r"^(ты молодец|ты умница|ты классный|ты классная)\b",
    r"^(ты долго думаешь|что-то ты долго думаешь|долго думаешь)\b",
    r"^(это странно|странно|что-то странно)\b",
    r"^(хорошо|ладно|понятно|ясно)\b",
    r"^(да|угу|ага|ну да)\b",
    r"^(нет|неа|не совсем)\b",
    r"^(не знаю|не уверен|может быть)\b",
    r"^(сомневаюсь|не уверен что это хорошая идея|не уверен что это сработает)\b",
    r"^(мне грустно|грустно|печально)\b",
    r"^(мне скучно|скучно)\b",
    r"^(я устал|я устала|устал|устала)\b",
    r"^(поддержи меня|мне нужна поддержка)\b",
    r"^(мне страшно|страшно)\b",
    r"^(я злюсь|я злая|я злой|злюсь)\b",
    r"^(меня бесит|это бесит|раздражает)\b",
    r"^(ха|аха|ахах|ха-ха|смешно)\b",
    r"^(расскажи сказку|хочу сказку|еще сказку|другую сказку)\b",
    r"^(расскажи короткую историю|хочу короткую историю|расскажи историю)\b",
    r"^(расскажи считалочку|хочу считалочку|скажи считалочку|расскажи рифмовку|еще считалочку|другую считалочку|еще рифмовку)\b",
    r"^(похвали меня|скажи что я молодец|я молодец\??)\b",
    r"^(мне сложно|у меня не получается|не получается)\b",
    r"^(я боюсь ошибиться|боюсь ошибиться)\b",
    r"^у тебя\b",
    r"^а у меня\b",
    r"^я думаю\b",
    r"^мне кажется\b",
)

_GAME_PATTERNS = (
    (r"игра(?:ть)? в слова", "words"),
    (r"поигра(?:ем|ть)? в слова", "words"),
    (r"игра(?:ть)? в прятки", "hide_and_seek"),
    (r"поигра(?:ем|ть)? в прятки", "hide_and_seek"),
    (r"игра(?:ть)? в загадки", "riddle"),
    (r"поигра(?:ем|ть)? в загадки", "riddle"),
    (r"угадай животное", "guess_animal"),
    (r"игра(?:ть)? в угадай животное", "guess_animal"),
    (r"поигра(?:ем|ть)? в угадай животное", "guess_animal"),
    (r"повтори за мной", "repeat_after_me"),
    (r"игра(?:ть)? в повтори за мной", "repeat_after_me"),
    (r"давай поиграем", None),
    (r"^еще$", "__repeat_last__"),
    (r"^еще раз$", "__repeat_last__"),
    (r"^давай еще$", "__repeat_last__"),
    (r"^давай еще раз$", "__repeat_last__"),
    (r"^еще загадку$", "riddle"),
    (r"^еще игру$", "__repeat_last__"),
)

_DATE_TAIL_PATTERN = re.compile(
    r"(?P<dt>(?:на\s+)?(?:сегодня|завтра|послезавтра)\b.*|"
    r"(?:на\s+)?через\s+\d+\s+д(?:ень|ня|ней)\b.*|"
    r"(?:на\s+)?\d{1,2}\s+"
    r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b.*|"
    r"(?:на\s+)?в\s+"
    r"(?:понедельник|вторник|сред[ау]|четверг|пятниц[ау]|суббот[ау]|воскресенье)\b.*)$"
)


def detect_fast_intent(user_text: str) -> IntentResult | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    create_task_prefixes = (
        "добавь задачу ",
        "создай задачу ",
        "запиши задачу ",
    )
    for prefix in create_task_prefixes:
        if normalized.startswith(prefix):
            remainder = normalized[len(prefix):].strip()
            task_text, dt_text = _split_text_and_datetime_tail(remainder)
            if task_text:
                data = {"task": task_text}
                if dt_text:
                    data["datetime"] = dt_text
                return IntentResult(intent="create_task", data=data)

    create_note_prefixes = (
        "запомни ",
        "добавь заметку ",
        "запиши заметку ",
        "сохрани заметку ",
    )
    for prefix in create_note_prefixes:
        if normalized.startswith(prefix):
            content = normalized[len(prefix):].strip(" .,:;!-")
            if prefix == "запомни ":
                personal_markers = (
                    "мне нравится",
                    "я люблю",
                    "мне не нравится",
                    "я не люблю",
                    "терпеть не могу",
                    "меня зовут",
                    "будь ",
                    "давай ",
                )
                if any(marker in content for marker in personal_markers):
                    break
            if content:
                return IntentResult(intent="create_note", data={"content": content})

    remember_profile_prefixes = (
        "запомни, что ",
        "запомни что ",
        "запомни обо мне ",
        "запомни про меня ",
    )
    for prefix in remember_profile_prefixes:
        if normalized.startswith(prefix):
            memory_text = normalized[len(prefix):].strip(" .,:;!-")
            if memory_text:
                return IntentResult(intent="remember_user_profile", data={"memory": memory_text})

    if normalized.startswith("запомни "):
        memory_text = normalized[len("запомни "):].strip(" .,:;!-")
        personal_markers = (
            "мне нравится",
            "я люблю",
            "мне не нравится",
            "я не люблю",
            "терпеть не могу",
            "меня зовут",
            "будь ",
            "давай ",
        )
        if memory_text and any(marker in memory_text for marker in personal_markers):
            return IntentResult(intent="remember_user_profile", data={"memory": memory_text})

    get_profile_variants = {
        "что ты обо мне помнишь",
        "что ты про меня помнишь",
        "что ты помнишь обо мне",
        "что ты помнишь про меня",
        "что ты знаешь обо мне",
        "мои предпочтения",
        "какие у меня предпочтения",
    }
    if normalized in get_profile_variants:
        return IntentResult(intent="get_user_profile", data={})

    forget_prefixes = (
        "забудь ",
        "удали из памяти ",
        "стереть из памяти ",
    )
    for prefix in forget_prefixes:
        if normalized.startswith(prefix):
            target = normalized[len(prefix):].strip(" .,:;!-")
            if target:
                return IntentResult(intent="forget_user_profile", data={"target": target})

    if normalized in {
        "очисти личную память",
        "сбрось личную память",
        "очистить личную память",
        "сбросить личную память",
        "забудь обо мне все",
        "забудь про меня все",
    }:
        return IntentResult(intent="forget_user_profile", data={"target": "все"})

    if normalized in {
        "что ты помнишь",
        "что у тебя в заметках",
        "покажи заметки",
        "какие у тебя заметки",
        "мои заметки",
        "заметки",
    }:
        return IntentResult(intent="get_notes", data={})

    if normalized in {
        "выгрузи заметки в обсидиан",
        "экспортируй заметки в обсидиан",
        "сохрани заметки в обсидиан",
        "выгрузи в обсидиан",
        "экспорт в обсидиан",
    }:
        return IntentResult(intent="export_notes", data={})

    append_obsidian_patterns = (
        r"^(?:добавь|запиши)\s+(?:в\s+)?обсидиан(?:\s+в\s+заметк[еу]\s+(.+?))?\s*[:\-]\s*(.+)$",
        r"^(?:добавь|запиши)\s+в\s+заметк[еу]\s+(.+?)\s+в\s+обсидиан\s*[:\-]\s*(.+)$",
    )
    for pattern in append_obsidian_patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        title = str(match.group(1) or "").strip(" .,:;!-") or "Vasya Note"
        text = str(match.group(2) or "").strip()
        if text:
            return IntentResult(intent="append_obsidian_note", data={"title": title, "text": text})

    replace_obsidian_patterns = (
        r"^(?:обнови|замени|перезапиши)\s+(?:заметк[ау]\s+)?(?:в\s+)?обсидиан(?:\s+(.+?))?\s*[:\-]\s*(.+)$",
        r"^(?:обнови|замени|перезапиши)\s+заметк[ау]\s+(.+?)\s+в\s+обсидиан\s*[:\-]\s*(.+)$",
    )
    for pattern in replace_obsidian_patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        title = str(match.group(1) or "").strip(" .,:;!-") or "Vasya Note"
        text = str(match.group(2) or "").strip()
        if text:
            return IntentResult(intent="replace_obsidian_note", data={"title": title, "text": text})

    sync_obsidian_patterns = (
        r"^(?:добавь|синхронизируй|обнови|сделай)\s+(?:проект\s+)?(?:github|гитхаб)\s+([\w.\-]+/[\w.\-]+)\s+(?:в|с)\s+обсидиан\b",
        r"^(?:добавь|синхронизируй|обнови)\s+проект\s+в\s+обсидиан\s+из\s+(?:github|гитхаб)(?:\s+([\w.\-]+/[\w.\-]+))?\b",
    )
    for pattern in sync_obsidian_patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        repo = ""
        for group_value in match.groups():
            if group_value:
                repo = str(group_value).strip()
                break
        data = {"repo": repo} if repo else {}
        return IntentResult(intent="sync_github_obsidian_project", data=data)

    if normalized in {
        "добавь проект github в обсидиан",
        "добавь проект гитхаб в обсидиан",
        "синхронизируй github в обсидиан",
        "синхронизируй гитхаб в обсидиан",
    }:
        return IntentResult(intent="sync_github_obsidian_project", data={})

    idea_plan_patterns = (
        r"^(?:проанализируй|разбери|оцени)\s+идею\s+(.+?)\s+в\s+заметк[уе]\s+(.+?)\s+в\s+обсидиан\b$",
        r"^(?:составь|распиши)\s+(?:план|задачи)\s+по\s+идее\s+(.+?)\s+в\s+заметк[уе]\s+(.+?)\s+в\s+обсидиан\b$",
        r"^(?:проанализируй|разбери|оцени)\s+(?:идею|идею проекта)\s*(.+?)?\s*(?:и|,)\s*(?:распиши|составь)\s+(?:план|задачи).*\bобсидиан\b$",
        r"^(?:составь|распиши)\s+(?:план|задачи)\s+по\s+идее\s+(.+?)\s+в\s+обсидиан\b$",
        r"^(?:проанализируй)\s+идею\s+(.+?)\s+и\s+запиши\s+в\s+обсидиан\b$",
    )
    for pattern in idea_plan_patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        idea_text = str(match.group(1) or "").strip(" .,:;!-")
        title_text = ""
        if len(match.groups()) >= 2:
            title_text = str(match.group(2) or "").strip(" .,:;!-")
        if idea_text:
            return IntentResult(
                intent="analyze_project_idea_to_obsidian",
                data={"idea": idea_text, **({"title": title_text} if title_text else {})},
            )

    idea_plan_prefixes = (
        "проанализируй идею проекта ",
        "проанализируй идею ",
        "составь план по идее ",
        "распиши задачи по идее ",
    )
    for prefix in idea_plan_prefixes:
        if not normalized.startswith(prefix):
            continue
        if "обсидиан" not in normalized:
            continue
        tail = normalized[len(prefix):].strip()
        title_text = ""
        title_match = re.search(r"\s+в\s+заметк[уе]\s+(.+?)\s+в\s+обсидиан\b", tail)
        if title_match:
            title_text = str(title_match.group(1) or "").strip(" .,:;!-")
            tail = re.sub(r"\s+в\s+заметк[уе]\s+.+?\s+в\s+обсидиан\b", "", tail).strip()
        if " в обсидиан" in tail:
            tail = tail.split(" в обсидиан", maxsplit=1)[0].strip()
        if tail:
            return IntentResult(
                intent="analyze_project_idea_to_obsidian",
                data={"idea": tail, **({"title": title_text} if title_text else {})},
            )

    sync_notion_patterns = (
        r"^(?:синхронизируй|обнови)\s+(?:github|гитхаб)(?:\s+([\w.\-]+/[\w.\-]+))?\s+(?:в|с)\s+(?:notion|ноушн)\b",
        r"^(?:синхронизируй|обнови)\s+(?:notion|ноушн)\s+по\s+(?:github|гитхаб)(?:\s+([\w.\-]+/[\w.\-]+))?\b",
    )
    for pattern in sync_notion_patterns:
        match = re.search(pattern, normalized)
        if match:
            repo = ""
            for group_value in match.groups():
                if group_value:
                    repo = str(group_value).strip()
                    break
            data = {"repo": repo} if repo else {}
            return IntentResult(intent="sync_github_notion", data=data)

    if normalized in {
        "прочитай notion",
        "прочитай ноушн",
        "что в notion",
        "что в ноушн",
        "покажи notion",
        "покажи ноушн",
    }:
        return IntentResult(intent="read_notion_page", data={})

    append_notion_prefixes = (
        "запиши в notion ",
        "запиши в ноушн ",
        "добавь в notion ",
        "добавь в ноушн ",
    )
    for prefix in append_notion_prefixes:
        if normalized.startswith(prefix):
            text = normalized[len(prefix):].strip(" .,:;!-")
            if text:
                return IntentResult(intent="append_notion_page", data={"text": text})

    open_url_prefixes = (
        "открой сайт ",
        "открой ссылку ",
        "перейди на ",
    )
    for prefix in open_url_prefixes:
        if normalized.startswith(prefix):
            url = normalized[len(prefix):].strip(" .,:;!-")
            if url:
                return IntentResult(intent="os_open_url", data={"url": url})

    open_app_patterns = (
        (r"^открой браузер\b", "Safari"),
        (r"^открой сафари\b", "Safari"),
        (r"^открой chrome\b", "Google Chrome"),
        (r"^открой хром\b", "Google Chrome"),
        (r"^открой notion\b", "Notion"),
        (r"^открой obsidian\b", "Obsidian"),
        (r"^открой терминал\b", "Terminal"),
        (r"^открой calendar\b", "Calendar"),
    )
    for pattern, app_name in open_app_patterns:
        if re.search(pattern, normalized):
            return IntentResult(intent="os_open_app", data={"app": app_name})

    type_prefixes = (
        "введи текст ",
        "напечатай ",
        "впиши ",
        "добавь текст ",
        "продиктуй ",
        "диктуй ",
        "вставь в открытую заметку ",
        "вставь в заметку ",
        "добавь в открытую заметку ",
        "добавь в заметку ",
        "вставь текст ",
        "вставь ",
    )
    for prefix in type_prefixes:
        if normalized.startswith(prefix):
            text = normalized[len(prefix):].strip()
            if text:
                return IntentResult(intent="os_type_text", data={"text": text})

    keypress_map = {
        "нажми enter": "enter",
        "нажми энтер": "enter",
        "нажми escape": "escape",
        "нажми esc": "esc",
        "нажми tab": "tab",
        "нажми пробел": "space",
        "нажми backspace": "backspace",
    }
    for phrase, key_name in keypress_map.items():
        if normalized == phrase:
            return IntentResult(intent="os_keypress", data={"keys": [key_name]})

    if normalized in {"кликни", "сделай клик", "нажми мышкой"}:
        return IntentResult(intent="os_click", data={"button": "left"})
    if normalized in {"правый клик", "кликни правой кнопкой"}:
        return IntentResult(intent="os_click", data={"button": "right"})
    if normalized in {"прокрути вниз", "скролл вниз"}:
        return IntentResult(intent="os_scroll", data={"amount": -700})
    if normalized in {"прокрути вверх", "скролл вверх"}:
        return IntentResult(intent="os_scroll", data={"amount": 700})

    list_tasks_patterns = (
        r"^(какие у меня задачи|какие задачи|есть ли у меня задачи|покажи задачи|список задач)\b",
    )
    for pattern in list_tasks_patterns:
        match = re.search(pattern, normalized)
        if match:
            remainder = normalized[match.end():].strip()
            dt_text = _extract_datetime_phrase(remainder)
            data = {"datetime": dt_text} if dt_text else {}
            return IntentResult(intent="get_tasks", data=data)

    list_events_patterns = (
        r"^(какие у меня дела|какие дела|какие события|покажи события|что в календаре|что у меня в календаре)\b",
    )
    for pattern in list_events_patterns:
        match = re.search(pattern, normalized)
        if match:
            remainder = normalized[match.end():].strip()
            dt_text = _extract_datetime_phrase(remainder)
            data = {"datetime": dt_text} if dt_text else {}
            return IntentResult(intent="get_events", data=data)

    if normalized in {"удали все задачи", "удали задачи", "очисти задачи"}:
        return IntentResult(intent="delete_tasks", data={"all": True})

    delete_task_prefixes = (
        "удали все задачи ",
        "очисти задачи ",
    )
    for prefix in delete_task_prefixes:
        if normalized.startswith(prefix):
            remainder = normalized[len(prefix):].strip()
            dt_text = _extract_datetime_phrase(remainder)
            if dt_text:
                return IntentResult(intent="delete_tasks", data={"all": True, "datetime": dt_text})

    if any(marker in normalized for marker in _COMMAND_MARKERS):
        return None

    for pattern, game_name in _GAME_PATTERNS:
        if re.search(pattern, normalized):
            data = {"game": game_name} if game_name else {}
            return IntentResult(intent="play_game", data=data)

    if normalized.endswith("?"):
        return IntentResult(intent="chat", data={})

    if any(re.search(pattern, normalized) for pattern in _CHAT_PATTERNS):
        return IntentResult(intent="chat", data={})

    return None


def detect_early_fast_intent(user_text: str) -> IntentResult | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    system_intent = detect_system_intent(normalized)
    if system_intent is not None:
        return system_intent

    if _looks_incomplete(normalized):
        return None

    fast_intent = detect_fast_intent(normalized)
    if fast_intent is None:
        return None

    if fast_intent.intent in {
        "get_tasks",
        "get_events",
        "delete_tasks",
        "play_game",
        "get_user_profile",
        "remember_user_profile",
        "forget_user_profile",
        "sync_github_notion",
        "sync_github_obsidian_project",
        "analyze_project_idea_to_obsidian",
        "read_notion_page",
        "append_notion_page",
        "append_obsidian_note",
        "replace_obsidian_note",
        "os_open_url",
        "os_open_app",
        "os_type_text",
        "os_keypress",
        "os_click",
        "os_scroll",
    }:
        return fast_intent

    if fast_intent.intent == "chat" and _is_safe_early_chat_text(normalized):
        return fast_intent

    return None


def _extract_datetime_phrase(text: str) -> str | None:
    if not text:
        return None
    match = _DATE_TAIL_PATTERN.search(text)
    if not match:
        return None
    return match.group("dt").strip()


def _split_text_and_datetime_tail(text: str) -> tuple[str, str | None]:
    dt_text = _extract_datetime_phrase(text)
    if not dt_text:
        return text.strip(), None

    dt_start = text.rfind(dt_text)
    if dt_start <= 0:
        return text.strip(), dt_text

    task_text = text[:dt_start].strip(" ,.-")
    return task_text, dt_text


def _looks_incomplete(text: str) -> bool:
    trailing_tokens = {
        "на",
        "в",
        "во",
        "к",
        "ко",
        "с",
        "со",
        "через",
        "и",
        "или",
        "все",
        "мне",
        "у",
    }
    if text.endswith(("...", ",", ".", ":", ";", "-", "—")):
        return True

    words = text.split()
    if not words:
        return True

    if words[-1] in trailing_tokens:
        return True

    if text.startswith(("добавь задачу", "создай задачу", "запиши задачу")):
        return True

    if text in {
        "какие",
        "какие задачи",
        "какие дела",
        "покажи",
        "покажи задачи",
        "покажи события",
        "удали",
        "удали все",
        "вставь",
        "продиктуй",
        "диктуй",
        "добавь текст",
        "введи текст",
        "напечатай",
    }:
        return True

    return False


def _is_safe_early_chat_text(text: str) -> bool:
    words = text.split()
    if len(words) > 5:
        return False

    trailing_tokens = {
        "и",
        "а",
        "но",
        "или",
        "что",
        "чтобы",
    }
    if words and words[-1] in trailing_tokens:
        return False

    return True
