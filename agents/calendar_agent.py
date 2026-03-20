from core.models import IntentResult
from services.calendar_service import create_event, get_events

def handle_calendar_intent(intent_result: IntentResult) -> str:
    if intent_result.intent == "create_event":
        title = intent_result.data.get("title", "Без названия")
        dt = intent_result.data.get("datetime")
        event = create_event(title=title, dt=dt)
        if event["datetime"]:
            return f"Добавил событие: {event['title']} на {event['datetime']}."
        return f"Добавил событие: {event['title']}."

    if intent_result.intent == "get_events":
        events = get_events()
        if not events:
            return "Событий пока нет."

        lines = []
        for idx, event in enumerate(events, start=1):
            if event.get("datetime"):
                lines.append(f"{idx}. {event['title']} — {event['datetime']}")
            else:
                lines.append(f"{idx}. {event['title']}")
        return "Вот события:\n" + "\n".join(lines)

    return "Не удалось обработать календарную команду."
