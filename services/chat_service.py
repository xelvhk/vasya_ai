from __future__ import annotations

import re
import time

from assistant.child_mode import child_mode_store
from assistant.conversation import conversation_memory
from assistant.state import AssistantStateName, assistant_state
from assistant.tone import conversation_tone
from assistant.user_profile import user_profile_memory
from config.settings import (
    OLLAMA_CHAT_QUICK_ENABLED,
    OLLAMA_CHAT_QUICK_MAX_WORDS,
    OLLAMA_CHAT_QUICK_MODEL,
    OLLAMA_CHAT_QUICK_NUM_PREDICT,
    OLLAMA_CHAT_STREAM,
    OLLAMA_CHAT_NUM_PREDICT,
    OLLAMA_CHAT_TEMPERATURE,
    OLLAMA_CHAT_THINK,
    OLLAMA_FAST_MODEL,
)
from services.memory_service import get_memory_snapshot, search_memory
from services.ollama_client import generate, generate_stream, resolve_chat_model
from utils.chat_fast_replies import generate_local_chat_reply
from utils.logger import log_voice_event


def generate_chat_reply(user_text: str) -> str:
    user_profile_memory.observe_user_text(user_text)
    recent_history = conversation_memory.recent()
    history_size = len(recent_history)
    last_assistant_reply = next(
        (message.content for message in reversed(recent_history) if message.role == "assistant"),
        None,
    )
    tone = conversation_tone.observe_user_text(user_text)
    child_mode = child_mode_store.is_enabled()
    if child_mode:
        safe_reply = _generate_child_safe_redirect(user_text)
        if safe_reply is not None:
            conversation_memory.add_user(user_text)
            conversation_memory.add_assistant(safe_reply)
            return safe_reply

    local_reply = generate_local_chat_reply(
        user_text,
        history_size=history_size,
        tone="child" if child_mode else tone,
        child_mode=child_mode,
        last_assistant_reply=last_assistant_reply,
    )
    if local_reply is not None:
        conversation_memory.add_user(user_text)
        conversation_memory.add_assistant(local_reply)
        return local_reply

    allow_greeting = _should_greet(user_text)
    memory_context = _build_memory_context(user_text)
    user_profile_hint = user_profile_memory.render_hint()
    use_quick_chat = _should_use_quick_chat(
        user_text,
        memory_context=memory_context,
        child_mode=child_mode,
    )
    prompt = _build_chat_prompt(
        user_text,
        allow_greeting=allow_greeting,
        tone="child" if child_mode else tone,
        child_mode=child_mode,
        memory_context=memory_context,
        user_profile_hint=user_profile_hint,
        compact=use_quick_chat,
    )
    model = _resolve_reply_model(use_quick_chat=use_quick_chat)
    num_predict = OLLAMA_CHAT_QUICK_NUM_PREDICT if use_quick_chat else OLLAMA_CHAT_NUM_PREDICT
    if OLLAMA_CHAT_STREAM:
        llm_started = time.perf_counter()
        reply = _generate_chat_reply_streaming(
            prompt,
            model=model,
            allow_greeting=allow_greeting,
            num_predict=num_predict,
        )
        llm_ms = (time.perf_counter() - llm_started) * 1000
        log_voice_event(
            f"chat_llm_ms={llm_ms:.0f} stream=true model={model} quick={str(use_quick_chat).lower()}"
        )
    else:
        llm_started = time.perf_counter()
        reply = generate(
            prompt,
            model=model,
            think=OLLAMA_CHAT_THINK,
            temperature=OLLAMA_CHAT_TEMPERATURE,
            num_predict=num_predict,
        )
        llm_ms = (time.perf_counter() - llm_started) * 1000
        log_voice_event(
            f"chat_llm_ms={llm_ms:.0f} stream=false model={model} quick={str(use_quick_chat).lower()}"
        )
        reply = _postprocess_chat_reply(reply, allow_greeting=allow_greeting)
    conversation_memory.add_user(user_text)
    conversation_memory.add_assistant(reply)
    return reply


def _build_chat_prompt(
    user_text: str,
    *,
    allow_greeting: bool,
    tone: str,
    child_mode: bool,
    memory_context: str | None = None,
    user_profile_hint: str | None = None,
    compact: bool = False,
) -> str:
    history_lines = []
    for message in conversation_memory.recent():
        role_label = "Пользователь" if message.role == "user" else "Вася"
        history_lines.append(f"{role_label}: {message.content}")

    history_limit = 2 if compact else 4
    history_block = "\n".join(history_lines[-history_limit:]) if history_lines else "История пока пустая."
    greeting_rule = (
        "Можно коротко поприветствовать пользователя, если это первое сообщение или он сам явно поздоровался."
        if allow_greeting
        else "Не начинай ответ с приветствия, если диалог уже идет."
    )
    tone_rule = _tone_rule(tone)
    child_rule = (
        "Детский режим включен: говори очень простыми словами, дружелюбно, безопасно, без 18+ тем, жестокости, наркотиков, сексуального контента и мрачных подробностей. Если пользователь спрашивает о таком, мягко откажись и предложи безопасную тему."
        if child_mode
        else "Ориентируйся на обычный дружелюбный режим."
    )
    memory_rule = (
        "Если в блоке 'Локальная память' есть релевантный контекст, используй его аккуратно и коротко. "
        "Если данных нет, честно скажи, что не нашла."
        if memory_context
        else "Не придумывай детали про прошлые задачи, заметки или события, если контекст не предоставлен."
    )
    memory_block = memory_context or "Локальная память не запрашивалась."
    profile_rule = (
        "Если есть блок 'Профиль пользователя', учитывай его как мягкие предпочтения тона и интересов."
        if user_profile_hint
        else "Если профиль пользователя не задан, не выдумывай персональные факты."
    )
    profile_block = user_profile_hint or "Профиль пользователя пока не заполнен."

    if compact:
        return f"""
Ты Вася, дружелюбный локальный AI-помощник.

Правила:
- Отвечай по-русски
- Ответ короткий: 1-2 фразы
- На "ты", естественно и без формальностей
- {greeting_rule}
- {tone_rule}
- {child_rule}
- {memory_rule}
- {profile_rule}

Недавняя история:
{history_block}

Локальная память:
{memory_block}

Профиль пользователя:
{profile_block}

Запрос:
{user_text}

Короткий ответ Васи:
""".strip()

    return f"""
Ты Вася, дружелюбный локальный AI-помощник.

Правила:
- Отвечай по-русски
- Говори естественно, кратко и по делу
- Обращайся к пользователю на "ты", а не на "вы"
- Тон дружелюбный, живой и неформальный, но без фамильярности
- Избегай канцелярита и слишком официальных формулировок
- Для обычной беседы чаще отвечай 1-2 короткими фразами, а не длинным монологом
- Если уместно, можно мягко задать один простой встречный вопрос, чтобы продолжить разговор
- Не повторяй дословно фразу пользователя без необходимости
- Не говори как справочник или техподдержка, говори как живой помощник
- Если пользователь отвечает коротко, например "угу", "да", "не знаю", "может быть", поддержи разговор естественно и помоги двинуться дальше
- Если пользователь делится усталостью, грустью, тревогой или раздражением, сначала отреагируй по-человечески и только потом предлагай следующий шаг
- Если пользователь легко перескакивает между разговором и практической просьбой, переходи мягко, без резкого канцелярского тона
- Можно поддерживать обычную беседу, объяснять, обсуждать идеи
- Не выдумывай доступ к внешним данным, файлам или действиям, если их не было
- Не оформляй ответ как JSON
- Не перечисляй длинные пункты без необходимости
- Не здоровайся в каждой реплике
- {greeting_rule}
- {tone_rule}
- {child_rule}
- {memory_rule}
- {profile_rule}

Недавняя история:
{history_block}

Локальная память:
{memory_block}

Профиль пользователя:
{profile_block}

Новый запрос пользователя:
{user_text}

Ответ Васи:
""".strip()


def _should_greet(user_text: str) -> bool:
    if conversation_memory.recent():
        return False
    normalized = user_text.strip().lower()
    return normalized.startswith(("привет", "здравствуй", "доброе утро", "добрый день", "добрый вечер"))


def _tone_rule(tone: str) -> str:
    if tone == "supportive":
        return "Сохраняй мягкий, поддерживающий и спокойный тон несколько реплик подряд, не становись резко сухим и не шути."
    if tone == "playful":
        return "Сохраняй легкий, живой и чуть более игровой тон, но не скатывайся в клоунаду. Иногда уместен очень короткий мягкий каламбур."
    if tone == "warm":
        return "Сохраняй теплый, дружелюбный и неформальный тон несколько реплик подряд. Редко можно позволить себе легкую словесную улыбку, если это уместно."
    if tone == "child":
        return "Сохраняй спокойный, добрый и детский тон, как у дружелюбного помощника для ребенка. Юмор только мягкий и безопасный."
    return "Держи спокойный дружелюбный нейтральный тон."


def _postprocess_chat_reply(reply: str, *, allow_greeting: bool) -> str:
    cleaned = reply.strip()
    cleaned = _soften_formality(cleaned)
    cleaned = _soften_robotic_openings(cleaned)
    cleaned = _shorten_reply(cleaned)
    if allow_greeting:
        return cleaned

    cleaned = re.sub(
        r"^(?:привет|здравствуй(?:те)?|доброе утро|добрый день|добрый вечер|хай)[!,.\s-]+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    if cleaned:
        return cleaned
    return reply.strip()


def _soften_formality(text: str) -> str:
    replacements = (
        (r"\bчто вы хотели бы\b", "что ты хотел бы"),
        (r"\bчто Вы хотели бы\b", "что ты хотел бы"),
        (r"\bесли вам нужно\b", "если тебе нужно"),
        (r"\bесли Вам нужно\b", "если тебе нужно"),
        (r"\bКак у вас дела\b", "Как у тебя дела"),
        (r"\bКак у вас\b", "Как у тебя"),
        (r"\bу вас\b", "у тебя"),
        (r"\bвам\b", "тебе"),
        (r"\bвас\b", "тебя"),
        (r"\bВам\b", "Тебе"),
        (r"\bВас\b", "Тебя"),
        (r"\bвы\b", "ты"),
        (r"\bВы\b", "Ты"),
    )
    softened = text
    for pattern, replacement in replacements:
        softened = re.sub(pattern, replacement, softened)
    softened = re.sub(r"\bРад слышать\b", "Рад это слышать", softened)
    softened = re.sub(r"\bРады слышать\b", "Рад это слышать", softened)
    softened = re.sub(r"\bКакой планы\b", "Какие планы", softened)
    return softened.strip()


def _soften_robotic_openings(text: str) -> str:
    softened = text.strip()
    softened = re.sub(r"^Конечно[!,.\s-]+", "", softened, flags=re.IGNORECASE).strip()
    softened = re.sub(r"^Разумеется[!,.\s-]+", "", softened, flags=re.IGNORECASE).strip()
    softened = re.sub(r"^Безусловно[!,.\s-]+", "", softened, flags=re.IGNORECASE).strip()
    softened = re.sub(
        r"^Я могу помочь тебе с этим[!.]?\s*",
        "Да, помогу. ",
        softened,
        flags=re.IGNORECASE,
    ).strip()
    softened = re.sub(
        r"^С удовольствием[!,.\s-]+",
        "",
        softened,
        flags=re.IGNORECASE,
    ).strip()
    return softened or text.strip()


def _shorten_reply(text: str) -> str:
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return text.strip()

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    if not sentences:
        return cleaned

    return " ".join(sentences[:2]).strip()


def _generate_chat_reply_streaming(
    prompt: str,
    *,
    model: str,
    allow_greeting: bool,
    num_predict: int,
) -> str:
    chunks: list[str] = []
    last_preview = ""
    started = time.perf_counter()
    first_token_ms: float | None = None
    for chunk in generate_stream(
        prompt,
        model=model,
        think=OLLAMA_CHAT_THINK,
        temperature=OLLAMA_CHAT_TEMPERATURE,
        num_predict=num_predict,
    ):
        if first_token_ms is None:
            first_token_ms = (time.perf_counter() - started) * 1000
        chunks.append(chunk)
        preview = _build_stream_preview("".join(chunks))
        if preview and preview != last_preview:
            assistant_state.set(AssistantStateName.THINKING, preview)
            last_preview = preview

    full_reply = "".join(chunks).strip()
    if first_token_ms is not None:
        log_voice_event(f"chat_first_token_ms={first_token_ms:.0f} model={model}")
    return _postprocess_chat_reply(full_reply, allow_greeting=allow_greeting)


def _should_use_quick_chat(
    user_text: str,
    *,
    memory_context: str | None,
    child_mode: bool,
) -> bool:
    if not OLLAMA_CHAT_QUICK_ENABLED:
        return False
    if child_mode:
        return False
    if memory_context:
        return False
    words = [part for part in re.split(r"\s+", user_text.strip()) if part]
    if not words:
        return False
    return len(words) <= max(1, OLLAMA_CHAT_QUICK_MAX_WORDS)


def _resolve_reply_model(*, use_quick_chat: bool) -> str:
    if not use_quick_chat:
        return resolve_chat_model()
    if OLLAMA_CHAT_QUICK_MODEL in {"", "fast"}:
        return OLLAMA_FAST_MODEL
    if OLLAMA_CHAT_QUICK_MODEL == "chat":
        return resolve_chat_model()
    return OLLAMA_CHAT_QUICK_MODEL


def _build_stream_preview(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "Формулирую ответ..."
    preview = cleaned[:120].rstrip()
    if len(cleaned) > 120:
        preview += "..."
    return preview


_MEMORY_QUERY_MARKERS = (
    "помнишь",
    "вспомни",
    "мы обсуждали",
    "что у меня",
    "какие у меня",
    "напомни",
    "прошл",
    "раньше",
    "вчера",
    "сегодня",
    "недавно",
    "заметк",
    "задач",
    "событ",
    "календар",
)

_GENERIC_MEMORY_QUERIES = (
    "что у меня",
    "какие у меня",
    "что было",
    "что нового",
    "что у нас",
    "вспомни",
    "напомни",
)


def _build_memory_context(user_text: str) -> str | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None
    if not any(marker in normalized for marker in _MEMORY_QUERY_MARKERS):
        return None

    try:
        query = _extract_memory_query(normalized)
        is_generic_query = not query or query in _GENERIC_MEMORY_QUERIES
        if is_generic_query:
            snapshot = get_memory_snapshot(limit_per_type=3)
            return _format_memory_snapshot(snapshot)

        matches = search_memory(query, limit_per_type=3)
        if _has_memory_matches(matches):
            return _format_memory_matches(matches)

        snapshot = get_memory_snapshot(limit_per_type=2)
        return _format_memory_snapshot(snapshot)
    except Exception:
        return None


def _extract_memory_query(normalized_text: str) -> str:
    query = normalized_text
    leading_patterns = (
        r"^(помнишь(?: ли)?(?:,)?\s*)",
        r"^(вспомни(?:,)?\s*)",
        r"^(напомни(?:,)?\s*)",
        r"^(скажи(?:,)?\s*)",
    )
    for pattern in leading_patterns:
        query = re.sub(pattern, "", query, flags=re.IGNORECASE).strip()

    query = re.sub(r"\b(что|какие|было|были|у|меня|мы|обсуждали|про|о)\b", " ", query)
    return " ".join(query.split()).strip()


def _has_memory_matches(matches: dict) -> bool:
    return bool(matches.get("notes") or matches.get("tasks") or matches.get("events"))


def _format_memory_matches(matches: dict) -> str:
    sections: list[str] = []
    notes = matches.get("notes", [])
    tasks = matches.get("tasks", [])
    events = matches.get("events", [])

    if notes:
        note_lines = [f"- {str(note.get('content', '')).strip()[:120]}" for note in notes]
        sections.append("Заметки:\n" + "\n".join(note_lines))

    if tasks:
        task_lines = [f"- {str(task.get('task', '')).strip()[:120]}" for task in tasks]
        sections.append("Задачи:\n" + "\n".join(task_lines))

    if events:
        event_lines = []
        for event in events:
            title = str(event.get("title", "")).strip()[:80]
            dt = str(event.get("date", "") or event.get("datetime", "")).strip()
            event_lines.append(f"- {title} ({dt})" if dt else f"- {title}")
        sections.append("События:\n" + "\n".join(event_lines))

    if not sections:
        return "Совпадений в локальной памяти нет."
    return "\n\n".join(sections)


def _format_memory_snapshot(snapshot: dict) -> str:
    sections: list[str] = []
    notes = snapshot.get("notes", {}).get("items", [])
    tasks = snapshot.get("tasks", {}).get("items", [])
    events = snapshot.get("events", {}).get("items", [])

    if notes:
        note_lines = [f"- {str(note.get('content', '')).strip()[:100]}" for note in notes]
        sections.append("Последние заметки:\n" + "\n".join(note_lines))
    else:
        sections.append("Последние заметки: пусто.")

    if tasks:
        task_lines = [f"- {str(task.get('task', '')).strip()[:100]}" for task in tasks]
        sections.append("Последние задачи:\n" + "\n".join(task_lines))
    else:
        sections.append("Последние задачи: пусто.")

    if events:
        event_lines = []
        for event in events:
            title = str(event.get("title", "")).strip()[:80]
            dt = str(event.get("date", "") or event.get("datetime", "")).strip()
            event_lines.append(f"- {title} ({dt})" if dt else f"- {title}")
        sections.append("Последние события:\n" + "\n".join(event_lines))
    else:
        sections.append("Последние события: пусто.")

    return "\n\n".join(sections)


def _generate_child_safe_redirect(user_text: str) -> str | None:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return None

    unsafe_patterns = (
        r"\bсекс\b",
        r"\bэрот",
        r"\b18\+\b",
        r"\bпорно\b",
        r"\bнаркот",
        r"\bубить\b",
        r"\bубий",
        r"\bсуиц",
        r"\bкров",
        r"\bжесток",
    )
    if any(re.search(pattern, normalized) for pattern in unsafe_patterns):
        return (
            "Давай лучше не будем про такие темы. "
            "Можем поговорить о животных, играх, космосе или придумать загадку."
        )
    return None
