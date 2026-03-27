from __future__ import annotations

import re

from assistant.conversation import conversation_memory
from assistant.state import AssistantStateName, assistant_state
from config.settings import (
    OLLAMA_CHAT_STREAM,
    OLLAMA_CHAT_NUM_PREDICT,
    OLLAMA_CHAT_TEMPERATURE,
    OLLAMA_CHAT_THINK,
)
from services.ollama_client import generate, generate_stream, resolve_chat_model


def generate_chat_reply(user_text: str) -> str:
    allow_greeting = _should_greet(user_text)
    prompt = _build_chat_prompt(user_text, allow_greeting=allow_greeting)
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


def _build_chat_prompt(user_text: str, *, allow_greeting: bool) -> str:
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

    return f"""
Ты Вася, дружелюбный локальный AI-помощник.

Правила:
- Отвечай по-русски
- Говори естественно, кратко и по делу
- Обращайся к пользователю на "ты", а не на "вы"
- Тон дружелюбный, живой и неформальный, но без фамильярности
- Избегай канцелярита и слишком официальных формулировок
- Можно поддерживать обычную беседу, объяснять, обсуждать идеи
- Не выдумывай доступ к внешним данным, файлам или действиям, если их не было
- Не оформляй ответ как JSON
- Не перечисляй длинные пункты без необходимости
- Не здоровайся в каждой реплике
- {greeting_rule}

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


def _postprocess_chat_reply(reply: str, *, allow_greeting: bool) -> str:
    cleaned = reply.strip()
    cleaned = _soften_formality(cleaned)
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
