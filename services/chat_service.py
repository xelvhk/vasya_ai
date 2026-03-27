from __future__ import annotations

from assistant.conversation import conversation_memory
from config.settings import (
    OLLAMA_CHAT_MODEL,
    OLLAMA_CHAT_NUM_PREDICT,
    OLLAMA_CHAT_TEMPERATURE,
    OLLAMA_CHAT_THINK,
)
from services.ollama_client import generate


def generate_chat_reply(user_text: str) -> str:
    prompt = _build_chat_prompt(user_text)
    reply = generate(
        prompt,
        model=OLLAMA_CHAT_MODEL,
        think=OLLAMA_CHAT_THINK,
        temperature=OLLAMA_CHAT_TEMPERATURE,
        num_predict=OLLAMA_CHAT_NUM_PREDICT,
    )
    conversation_memory.add_user(user_text)
    conversation_memory.add_assistant(reply)
    return reply


def _build_chat_prompt(user_text: str) -> str:
    history_lines = []
    for message in conversation_memory.recent():
        role_label = "Пользователь" if message.role == "user" else "Вася"
        history_lines.append(f"{role_label}: {message.content}")

    history_block = "\n".join(history_lines) if history_lines else "История пока пустая."

    return f"""
Ты Вася, дружелюбный локальный AI-помощник.

Правила:
- Отвечай по-русски
- Говори естественно, кратко и по делу
- Можно поддерживать обычную беседу, объяснять, обсуждать идеи
- Не выдумывай доступ к внешним данным, файлам или действиям, если их не было
- Не оформляй ответ как JSON
- Не перечисляй длинные пункты без необходимости

Недавняя история:
{history_block}

Новый запрос пользователя:
{user_text}

Ответ Васи:
""".strip()
