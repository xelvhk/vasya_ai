from core.models import IntentResult
from services.calendar_service import create_event, get_events
from utils.datetime_parser import normalize_datetime

def handle_calendar_intent(intent_result: IntentResult) -> str:
    if intent_result.intent == "create_event":
        title = intent_result.data.get("title", "Без названия")
        raw_dt = intent_result.data.get("datetime")
        spoken_dt = raw_dt.strip() if isinstance(raw_dt, str) else None
        normalized_dt = normalize_datetime(raw_dt)
        event = create_event(title=title, dt=normalized_dt)
        if normalized_dt:
            if spoken_dt:
                return f"Добавил событие: {event['title']} на {spoken_dt}."
            return f"Добавил событие: {event['title']} на {event['datetime']}."
        if raw_dt:
            return (
                f"Добавил событие: {event['title']}, "
                "но дату и время распознать надежно не удалось."
            )
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
