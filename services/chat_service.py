from __future__ import annotations

import re

from assistant.child_mode import child_mode_store
from assistant.conversation import conversation_memory
from assistant.state import AssistantStateName, assistant_state
from assistant.tone import conversation_tone
from config.settings import (
    OLLAMA_CHAT_STREAM,
    OLLAMA_CHAT_NUM_PREDICT,
    OLLAMA_CHAT_TEMPERATURE,
    OLLAMA_CHAT_THINK,
)
from services.ollama_client import generate, generate_stream, resolve_chat_model
from utils.chat_fast_replies import generate_local_chat_reply


def generate_chat_reply(user_text: str) -> str:
    history_size = len(conversation_memory.recent())
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
    )
    if local_reply is not None:
        conversation_memory.add_user(user_text)
        conversation_memory.add_assistant(local_reply)
        return local_reply

    allow_greeting = _should_greet(user_text)
    prompt = _build_chat_prompt(
        user_text,
        allow_greeting=allow_greeting,
        tone="child" if child_mode else tone,
        child_mode=child_mode,
    )
    model = resolve_chat_model()
    if OLLAMA_CHAT_STREAM:
        reply = _generate_chat_reply_streaming(
            prompt,
            model=model,
            allow_greeting=allow_greeting,
        )
    else:
        reply = generate(
            prompt,
            model=model,
            think=OLLAMA_CHAT_THINK,
            temperature=OLLAMA_CHAT_TEMPERATURE,
            num_predict=OLLAMA_CHAT_NUM_PREDICT,
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
) -> str:
    history_lines = []
    for message in conversation_memory.recent():
        role_label = "Пользователь" if message.role == "user" else "Вася"
        history_lines.append(f"{role_label}: {message.content}")

    history_block = "\n".join(history_lines) if history_lines else "История пока пустая."
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

    return f"""
Ты Вася, дружелюбный локальный AI-помощник.

Правила:
- Отвечай по-русски
- Говори естественно, кратко и по делу
- Обращайся к пользователю на "ты", а не на "вы"
- Тон дружелюбный, живой и неформальный, но без фамильярности
- Избегай канцелярита и слишком официальных формулировок
- Для обычной беседы чаще отвечай 1-3 короткими фразами, а не длинным монологом
- Если уместно, можно мягко задать один простой встречный вопрос, чтобы продолжить разговор
- Не повторяй дословно фразу пользователя без необходимости
- Не говори как справочник или техподдержка, говори как живой помощник
- Если пользователь отвечает коротко, например "угу", "да", "не знаю", "может быть", поддержи разговор естественно и помоги двинуться дальше
- Если пользователь делится усталостью, грустью, тревогой или раздражением, сначала отреагируй по-человечески и только потом предлагай следующий шаг
- Можно поддерживать обычную беседу, объяснять, обсуждать идеи
- Не выдумывай доступ к внешним данным, файлам или действиям, если их не было
- Не оформляй ответ как JSON
- Не перечисляй длинные пункты без необходимости
- Не здоровайся в каждой реплике
- {greeting_rule}
- {tone_rule}
- {child_rule}

Недавняя история:
{history_block}

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
        return "Сохраняй мягкий, поддерживающий и спокойный тон несколько реплик подряд, не становись резко сухим."
    if tone == "playful":
        return "Сохраняй легкий, живой и чуть более игровой тон, но не скатывайся в клоунаду."
    if tone == "warm":
        return "Сохраняй теплый, дружелюбный и неформальный тон несколько реплик подряд."
    if tone == "child":
        return "Сохраняй спокойный, добрый и детский тон, как у дружелюбного помощника для ребенка."
    return "Держи спокойный дружелюбный нейтральный тон."


def _postprocess_chat_reply(reply: str, *, allow_greeting: bool) -> str:
    cleaned = reply.strip()
    cleaned = _soften_formality(cleaned)
    cleaned = _soften_robotic_openings(cleaned)
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


def _generate_chat_reply_streaming(
    prompt: str,
    *,
    model: str,
    allow_greeting: bool,
) -> str:
    chunks: list[str] = []
    last_preview = ""
    for chunk in generate_stream(
        prompt,
        model=model,
        think=OLLAMA_CHAT_THINK,
        temperature=OLLAMA_CHAT_TEMPERATURE,
        num_predict=OLLAMA_CHAT_NUM_PREDICT,
    ):
        chunks.append(chunk)
        preview = _build_stream_preview("".join(chunks))
        if preview and preview != last_preview:
            assistant_state.set(AssistantStateName.THINKING, preview)
            last_preview = preview

    full_reply = "".join(chunks).strip()
    return _postprocess_chat_reply(full_reply, allow_greeting=allow_greeting)


def _build_stream_preview(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "Формулирую ответ..."
    preview = cleaned[:120].rstrip()
    if len(cleaned) > 120:
        preview += "..."
    return preview


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
