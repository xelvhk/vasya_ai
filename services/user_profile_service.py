from __future__ import annotations

from assistant.user_profile import user_profile_memory


def remember_user_profile(memory_text: str) -> str:
    normalized = " ".join(str(memory_text).strip().split())
    if not normalized:
        return "Не расслышала, что именно запомнить о тебе."
    changed = user_profile_memory.remember_explicit(normalized)
    if not changed:
        return "Это уже есть в моей личной памяти о тебе."
    return "Запомнила про тебя. Учту это дальше."


def forget_user_profile(target_text: str) -> str:
    normalized = " ".join(str(target_text).strip().split())
    if not normalized:
        return "Скажи, что именно убрать из личной памяти."
    changed = user_profile_memory.forget_explicit(normalized)
    if not changed:
        return "Не нашла это в личной памяти."
    return "Готово, убрала это из личной памяти."


def get_user_profile_summary() -> str:
    return user_profile_memory.summary_text()


def clear_user_profile() -> str:
    changed = user_profile_memory.clear_all()
    if not changed:
        return "Личная память уже пустая."
    return "Личную память очистила."
