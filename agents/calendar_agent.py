from core.models import IntentResult
from services.calendar_service import create_event, get_events
from utils.datetime_parser import parse_datetime

def handle_calendar_intent(intent_result: IntentResult) -> str:
    if intent_result.intent == "create_event":
        title = intent_result.data.get("title", "Без названия")
        raw_dt = intent_result.data.get("datetime")
        spoken_dt = raw_dt.strip() if isinstance(raw_dt, str) else None
        parse_result = parse_datetime(raw_dt)
        event = create_event(title=title, dt=parse_result.normalized)
        if parse_result.normalized:
            if spoken_dt:
                if parse_result.status == "parsed_with_default_time" and parse_result.message:
                    return (
                        f"Добавил событие: {event['title']} на {spoken_dt}. "
                        f"{parse_result.message}"
                    )
                return f"Добавил событие: {event['title']} на {spoken_dt}."
            return f"Добавил событие: {event['title']} на {event['datetime']}."
        if raw_dt:
            if parse_result.status == "ambiguous" and parse_result.message:
                return (
                    f"Добавил событие: {event['title']}, "
                    f"но дату и время нужно уточнить. {parse_result.message}"
                )
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
