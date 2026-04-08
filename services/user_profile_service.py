from __future__ import annotations

from assistant.confirmations import confirmation_store
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


def request_clear_user_profile_confirmation() -> str:
    item_count = user_profile_memory.total_items()
    if item_count <= 0:
        return "Личная память уже пустая."
    confirmation_store.set("clear_user_profile", {"items": item_count})
    return (
        f"Это очистит личную память о тебе, сейчас там {_pluralize_items(item_count)}. "
        "Подтверди: скажи да или нет."
    )


def confirm_clear_user_profile() -> str:
    return clear_user_profile()


def is_clear_all_target(target_text: str) -> bool:
    normalized = " ".join(str(target_text).lower().strip().split())
    clear_all_variants = {
        "все",
        "всё",
        "все это",
        "всё это",
        "всю память",
        "все что помнишь",
        "всё что помнишь",
        "обо мне все",
        "личную память",
        "личная память",
    }
    return normalized in clear_all_variants


def _pluralize_items(count: int) -> str:
    mod10 = count % 10
    mod100 = count % 100
    if mod10 == 1 and mod100 != 11:
        return f"{count} пункт"
    if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
        return f"{count} пункта"
    return f"{count} пунктов"
