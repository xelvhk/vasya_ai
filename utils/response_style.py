from __future__ import annotations


def pick_variant(key: str, *options: str) -> str:
    cleaned = [option for option in options if option]
    if not cleaned:
        return ""
    index = abs(hash(key)) % len(cleaned)
    return cleaned[index]


def join_spoken_list(items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} и {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])} и {cleaned[-1]}"


def pluralize_tasks(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} задача"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f"{count} задачи"
    return f"{count} задач"


def pluralize_events(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} событие"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f"{count} события"
    return f"{count} событий"
