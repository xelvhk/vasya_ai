from core.models import IntentResult
from services.task_service import (
    complete_task,
    create_task,
    delete_task,
    delete_tasks_by_date,
    get_tasks,
)
from utils.datetime_parser import parse_datetime
from utils.humanize import humanize_event_datetime


def handle_task_intent(intent_result: IntentResult) -> str:
    if intent_result.intent == "create_task":
        task_text = intent_result.data.get("task", "").strip()
        raw_dt = intent_result.data.get("datetime")
        if not task_text:
            return "Я не расслышал текст задачи."

        normalized_dt = None
        if isinstance(raw_dt, str) and raw_dt.strip():
            parse_result = parse_datetime(raw_dt)
            normalized_dt = parse_result.normalized

        task = create_task(task_text, dt=normalized_dt)
        if task.get("datetime"):
            spoken_datetime = humanize_event_datetime(task["datetime"]) or task["datetime"]
            return f"Добавил в задачи: {task['task']} на {spoken_datetime}."
        return f"Добавил в задачи: {task['task']}."

    if intent_result.intent == "get_tasks":
        filter_date, date_context, error = _extract_date_filter(intent_result.data.get("datetime"))
        if error:
            return error

        tasks = get_tasks(filter_date=filter_date)
        if not tasks:
            if date_context:
                return f"На {date_context} задач нет."
            return "Задач пока нет."

        lines = []
        for idx, item in enumerate(tasks, start=1):
            if item.get("datetime"):
                spoken_datetime = humanize_event_datetime(item["datetime"]) or item["datetime"]
                lines.append(f"{idx}. {item['task']} — {spoken_datetime}")
            else:
                lines.append(f"{idx}. {item['task']}")

        count = len(tasks)
        if date_context:
            prefix = f"Вот задачи на {date_context}:"
        elif count == 1:
            prefix = "Сейчас у тебя 1 задача:"
        elif 2 <= count <= 4:
            prefix = f"Сейчас у тебя {count} задачи:"
        else:
            prefix = f"Сейчас у тебя {count} задач:"
        return prefix + "\n" + "\n".join(lines)

    if intent_result.intent == "complete_task":
        target = intent_result.data.get("target", "")
        tasks = get_tasks()
        resolved = _resolve_task_target(tasks, target)
        if not resolved:
            return "Не нашел такую задачу, чтобы отметить выполненной."

        task = complete_task(resolved["id"])
        if not task:
            return "Не удалось отметить задачу выполненной."
        return f"Отметил как выполненную: {task['task']}."

    if intent_result.intent == "delete_task":
        target = intent_result.data.get("target", "")
        tasks = get_tasks()
        resolved = _resolve_task_target(tasks, target)
        if not resolved:
            return "Не нашел такую задачу для удаления."

        deleted = delete_task(resolved["id"])
        if not deleted:
            return "Не удалось удалить задачу."
        return f"Удалил задачу: {resolved['task']}."

    if intent_result.intent == "delete_tasks":
        filter_date, date_context, error = _extract_date_filter(intent_result.data.get("datetime"))
        if error:
            return error
        if not filter_date:
            return "Нужно уточнить дату, для которой удалить задачи."

        deleted_count = delete_tasks_by_date(filter_date)
        if deleted_count == 0:
            return f"На {date_context or filter_date} задач для удаления нет."
        if deleted_count == 1:
            return f"Удалил 1 задачу на {date_context or filter_date}."
        return (
            f"Удалил {_format_task_count(deleted_count)} "
            f"на {date_context or filter_date}."
        )

    return "Не удалось обработать команду по задачам."


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
        return None, None, "Не удалось распознать дату для задач."

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
