from assistant.confirmations import confirmation_store
from core.models import IntentResult
from services.task_service import (
    count_open_tasks,
    complete_task,
    create_task,
    delete_all_tasks,
    delete_task,
    delete_tasks_by_date,
    get_tasks,
)
from utils.datetime_parser import parse_datetime
from utils.humanize import humanize_event_datetime
from utils.response_style import join_spoken_list, pick_variant, pluralize_tasks


def handle_task_intent(intent_result: IntentResult) -> str:
    if intent_result.intent == "create_task":
        task_text = intent_result.data.get("task", "").strip()
        raw_dt = intent_result.data.get("datetime")
        if not task_text:
            return (
                "Не расслышала, что именно добавить в задачи. "
                "Скажи, например: добавь задачу купить молоко."
            )

        normalized_dt = None
        if isinstance(raw_dt, str) and raw_dt.strip():
            parse_result = parse_datetime(raw_dt)
            normalized_dt = parse_result.normalized

        task = create_task(task_text, dt=normalized_dt)
        if task.get("datetime"):
            spoken_datetime = humanize_event_datetime(task["datetime"]) or task["datetime"]
            prefix = pick_variant(
                task["task"],
                "Готово. Добавил задачу:",
                "Сделано. Добавил задачу:",
                "Хорошо. Добавил задачу:",
            )
            return f"{prefix} {task['task']} на {spoken_datetime}."
        prefix = pick_variant(
            task["task"],
            "Готово. Добавил задачу:",
            "Сделано. Добавил задачу:",
            "Хорошо. Добавил задачу:",
        )
        return f"{prefix} {task['task']}."

    if intent_result.intent == "get_tasks":
        filter_date, date_context, error = _extract_date_filter(intent_result.data.get("datetime"))
        if error:
            return error

        tasks = get_tasks(filter_date=filter_date)
        if not tasks:
            if date_context:
                return f"На {date_context} у тебя задач нет."
            return "Пока задач нет."

        spoken_items = []
        for item in tasks:
            if item.get("datetime"):
                spoken_datetime = humanize_event_datetime(item["datetime"]) or item["datetime"]
                spoken_items.append(f"{item['task']} на {spoken_datetime}")
            else:
                spoken_items.append(item["task"])

        count = len(tasks)
        if date_context:
            if count == 1:
                return f"На {date_context} у тебя одна задача: {spoken_items[0]}."
            return f"На {date_context} у тебя {pluralize_tasks(count)}: {join_spoken_list(spoken_items)}."
        if count == 1:
            return f"Сейчас у тебя одна задача: {spoken_items[0]}."
        if count <= 4:
            return f"Сейчас у тебя {pluralize_tasks(count)}: {join_spoken_list(spoken_items)}."
        if count <= 8:
            return f"Сейчас у тебя {pluralize_tasks(count)}. Вот что есть: {join_spoken_list(spoken_items)}."
        else:
            preview = join_spoken_list(spoken_items[:5])
            return (
                f"Сейчас у тебя {pluralize_tasks(count)}. "
                f"Из ближайшего: {preview}."
            )

    if intent_result.intent == "complete_task":
        target = intent_result.data.get("target", "")
        if not str(target).strip():
            return "Скажи, какую задачу отметить выполненной. Можно по названию или по номеру из списка."
        tasks = get_tasks()
        resolved = _resolve_task_target(tasks, target)
        if not resolved:
            return "Не нашла такую задачу. Скажи название точнее или номер из списка."

        task = complete_task(resolved["id"])
        if not task:
            return "Не удалось отметить задачу выполненной."
        prefix = pick_variant(
            task["task"],
            "Отлично. Отметил как выполненную:",
            "Готово. Отметил как выполненную:",
            "Хорошо. Отметил как выполненную:",
        )
        return f"{prefix} {task['task']}."

    if intent_result.intent == "delete_task":
        target = intent_result.data.get("target", "")
        if not str(target).strip():
            return "Скажи, какую задачу удалить. Можно по названию или по номеру из списка."
        tasks = get_tasks()
        resolved = _resolve_task_target(tasks, target)
        if not resolved:
            return "Не нашла такую задачу для удаления. Скажи название точнее или номер из списка."

        deleted = delete_task(resolved["id"])
        if not deleted:
            return "Не удалось удалить задачу."
        prefix = pick_variant(
            resolved["task"],
            "Хорошо. Удалил задачу:",
            "Готово. Удалил задачу:",
            "Сделано. Удалил задачу:",
        )
        return f"{prefix} {resolved['task']}."

    if intent_result.intent == "delete_tasks":
        if intent_result.data.get("all") is True:
            open_count = count_open_tasks()
            if open_count == 0:
                return "Открытых задач сейчас нет."
            confirmation_store.set("delete_all_tasks", {"count": open_count})
            return (
                f"Это удалит все открытые задачи, сейчас их {open_count}. "
                "Подтверди: скажи да или нет."
            )

        filter_date, date_context, error = _extract_date_filter(intent_result.data.get("datetime"))
        if error:
            return error
        if not filter_date:
            return (
                "Нужно уточнить дату, для которой удалить задачи. "
                "Например: удали все задачи на завтра."
            )

        deleted_count = delete_tasks_by_date(filter_date)
        if deleted_count == 0:
            return f"На {date_context or filter_date} задач для удаления нет."
        if deleted_count == 1:
            prefix = pick_variant(
                f"{date_context or filter_date}:1",
                "Хорошо. Удалил одну задачу",
                "Готово. Удалил одну задачу",
            )
            return f"{prefix} на {date_context or filter_date}."
        return (
            f"{pick_variant(f'{date_context or filter_date}:{deleted_count}', 'Хорошо. Удалил', 'Готово. Удалил')} "
            f"{_format_task_count(deleted_count)} "
            f"на {date_context or filter_date}."
        )

    return "Не удалось обработать команду по задачам."


def confirm_delete_all_tasks() -> str:
    deleted_count = delete_all_tasks()
    if deleted_count == 0:
        return "Открытых задач для удаления не осталось."
    if deleted_count == 1:
        return pick_variant(
            "confirm_delete_all_tasks:1",
            "Хорошо. Удалил одну задачу.",
            "Готово. Удалил одну задачу.",
        )
    prefix = pick_variant(
        f"confirm_delete_all_tasks:{deleted_count}",
        "Хорошо. Удалил",
        "Готово. Удалил",
    )
    return f"{prefix} {_format_task_count(deleted_count)}."


def _resolve_task_target(tasks: list[dict], target: str) -> dict | None:
    normalized_target = str(target).strip()
    if not normalized_target:
        return None

    if normalized_target.isdigit():
        index = int(normalized_target) - 1
        if 0 <= index < len(tasks):
            return tasks[index]
        return None

    lowered_target = normalized_target.casefold()
    for item in tasks:
        task_text = item.get("task", "")
        if task_text.casefold() == lowered_target:
            return item

    for item in tasks:
        task_text = item.get("task", "")
        if lowered_target in task_text.casefold():
            return item

    return None


def _extract_date_filter(raw_dt: object) -> tuple[str | None, str | None, str | None]:
    if not isinstance(raw_dt, str) or not raw_dt.strip():
        return None, None, None

    parse_result = parse_datetime(raw_dt)
    if parse_result.status == "ambiguous" and parse_result.message:
        return None, None, (
            "Нужно уточнить дату для задач. "
            f"{parse_result.message}"
        )
    if not parse_result.normalized:
        return None, None, "Не удалось распознать дату для задач. Попробуй сказать, например: на завтра или на 25 марта."

    date_context = raw_dt.strip()
    if date_context.lower().startswith("на "):
        date_context = date_context[3:].strip()
    return parse_result.normalized.split(" ")[0], date_context, None


def _format_task_count(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} задачу"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f"{count} задачи"
    return f"{count} задач"
