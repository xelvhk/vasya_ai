from core.models import IntentResult
from services.task_service import create_task, get_tasks

def handle_task_intent(intent_result: IntentResult) -> str:
    if intent_result.intent == "create_task":
        task_text = intent_result.data.get("task", "").strip()
        if not task_text:
            return "Я не расслышал текст задачи."

        task = create_task(task_text)
        return f"Добавил задачу: {task['task']}."

    if intent_result.intent == "get_tasks":
        tasks = get_tasks()
        if not tasks:
            return "Задач пока нет."

        lines = [f"{idx}. {item['task']}" for idx, item in enumerate(tasks, start=1)]
        return "Вот задачи:\n" + "\n".join(lines)

    return "Не удалось обработать команду по задачам."