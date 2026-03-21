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
        google_sync_error = event.get("google_sync_error")
        if parse_result.normalized:
            if spoken_dt:
                if parse_result.status == "parsed_with_default_time" and parse_result.message:
                    if google_sync_error:
                        return (
                            f"Добавил событие: {event['title']} на {spoken_dt}. "
                            f"{parse_result.message} "
                            f"Google Calendar не синхронизирован: {google_sync_error}"
                        )
                    return (
                        f"Добавил событие: {event['title']} на {spoken_dt}. "
                        f"{parse_result.message}"
                    )
                if google_sync_error:
                    return (
                        f"Добавил событие: {event['title']} на {spoken_dt}. "
                        f"Google Calendar не синхронизирован: {google_sync_error}"
                    )
                return f"Добавил событие: {event['title']} на {spoken_dt}."
            if google_sync_error:
                return (
                    f"Добавил событие: {event['title']} на {event['datetime']}. "
                    f"Google Calendar не синхронизирован: {google_sync_error}"
                )
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
        raw_dt = intent_result.data.get("datetime")
        filter_date = None
        date_context = None

        if isinstance(raw_dt, str) and raw_dt.strip():
            parse_result = parse_datetime(raw_dt)
            if parse_result.status == "ambiguous" and parse_result.message:
                return (
                    "Нужно уточнить, на какую дату показать события. "
                    f"{parse_result.message}"
                )
            if parse_result.normalized:
                filter_date = parse_result.normalized.split(" ")[0]
                date_context = raw_dt.strip()

        result = get_events(filter_date=filter_date)
        events = result["events"]
        google_sync_error = result.get("google_sync_error")
        if not events:
            if date_context:
                if google_sync_error:
                    return (
                        f"На {date_context} событий нет. "
                        f"Google Calendar не синхронизирован: {google_sync_error}"
                    )
                return f"На {date_context} событий нет."
            if google_sync_error:
                return (
                    "Событий пока нет. "
                    f"Google Calendar не синхронизирован: {google_sync_error}"
                )
            return "Событий пока нет."

        lines = []
        for idx, event in enumerate(events, start=1):
            if event.get("datetime"):
                lines.append(f"{idx}. {event['title']} — {event['datetime']}")
            else:
                lines.append(f"{idx}. {event['title']}")
        prefix = "Вот события:"
        if date_context:
            normalized_context = date_context
            if normalized_context.lower().startswith("на "):
                prefix = f"Вот события {normalized_context}:"
            else:
                prefix = f"Вот события на {normalized_context}:"
        if google_sync_error:
            return (
                prefix
                + "\n"
                + "\n".join(lines)
                + f"\n\nGoogle Calendar не синхронизирован: {google_sync_error}"
            )
        return prefix + "\n" + "\n".join(lines)

    return "Не удалось обработать календарную команду."
