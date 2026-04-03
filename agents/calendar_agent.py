from core.models import IntentResult
from services.calendar_service import create_event, delete_event, get_events
from utils.datetime_parser import parse_datetime
from utils.humanize import humanize_event_datetime
from utils.response_style import join_spoken_list, pick_variant, pluralize_events

def handle_calendar_intent(intent_result: IntentResult) -> str:
    if intent_result.intent == "create_event":
        title = str(intent_result.data.get("title", "")).strip()
        raw_dt = intent_result.data.get("datetime")
        if not title:
            return (
                "Не расслышала, как назвать событие. "
                "Скажи, например: добавь событие созвон с командой завтра в 15:00."
            )
        spoken_dt = raw_dt.strip() if isinstance(raw_dt, str) else None
        parse_result = parse_datetime(raw_dt)
        event = create_event(title=title, dt=parse_result.normalized)
        google_sync_error = event.get("google_sync_error")
        if parse_result.normalized:
            if spoken_dt:
                added_prefix = pick_variant(
                    title,
                    "Готово. Добавил событие:",
                    "Сделано. Добавил событие:",
                    "Хорошо. Добавил событие:",
                )
                if parse_result.status == "parsed_with_default_time" and parse_result.message:
                    if google_sync_error:
                        return (
                            f"{added_prefix} {event['title']} на {spoken_dt}. "
                            f"{parse_result.message} "
                            f"Google Calendar не синхронизирован: {google_sync_error}"
                        )
                    return (
                        f"{added_prefix} {event['title']} на {spoken_dt}. "
                        f"{parse_result.message}"
                    )
                if google_sync_error:
                    return (
                        f"{added_prefix} {event['title']} на {spoken_dt}. "
                        f"Google Calendar не синхронизирован: {google_sync_error}"
                    )
                return f"{added_prefix} {event['title']} на {spoken_dt}."
            if google_sync_error:
                added_prefix = pick_variant(
                    title,
                    "Готово. Добавил событие:",
                    "Сделано. Добавил событие:",
                    "Хорошо. Добавил событие:",
                )
                return (
                    f"{added_prefix} {event['title']} на {event['datetime']}. "
                    f"Google Calendar не синхронизирован: {google_sync_error}"
                )
            added_prefix = pick_variant(
                title,
                "Готово. Добавил событие:",
                "Сделано. Добавил событие:",
                "Хорошо. Добавил событие:",
            )
            return f"{added_prefix} {event['title']} на {event['datetime']}."
        if raw_dt:
            if parse_result.status == "ambiguous" and parse_result.message:
                return (
                    f"Событие добавил: {event['title']}, "
                    f"но дату и время нужно уточнить. {parse_result.message}"
                )
            return (
                f"Событие добавил: {event['title']}, "
                "но дату и время распознать надежно не удалось."
            )
        added_prefix = pick_variant(
            title,
            "Готово. Добавил событие:",
            "Сделано. Добавил событие:",
            "Хорошо. Добавил событие:",
        )
        return f"{added_prefix} {event['title']}."

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
            if not parse_result.normalized:
                return (
                    "Не удалось распознать дату для событий. "
                    "Попробуй сказать, например: на завтра или на 25 марта."
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
                        f"На {date_context} у тебя событий нет. "
                        f"Google Calendar не синхронизирован: {google_sync_error}"
                    )
                return f"На {date_context} у тебя событий нет."
            if google_sync_error:
                return (
                    "Пока событий нет. "
                    f"Google Calendar не синхронизирован: {google_sync_error}"
                )
            return "Пока событий нет."

        spoken_items = []
        for event in events:
            if event.get("datetime"):
                spoken_datetime = humanize_event_datetime(event["datetime"]) or event["datetime"]
                spoken_items.append(f"{event['title']} — {spoken_datetime}")
            else:
                spoken_items.append(event["title"])

        count = len(events)
        if date_context:
            normalized_context = date_context
            if normalized_context.lower().startswith("на "):
                prefix = f"На {normalized_context} у тебя"
            else:
                prefix = f"На {normalized_context} у тебя"
            if count == 1:
                base_response = f"{prefix} одно событие: {spoken_items[0]}."
            else:
                base_response = (
                    f"{prefix} {pluralize_events(count)}: "
                    f"{join_spoken_list(spoken_items)}."
                )
        elif count == 1:
            base_response = f"У тебя одно событие: {spoken_items[0]}."
        elif count <= 4:
            base_response = (
                f"У тебя {pluralize_events(count)}: "
                f"{join_spoken_list(spoken_items)}."
            )
        elif count <= 8:
            base_response = (
                f"У тебя {pluralize_events(count)}. "
                f"Вот что есть: {join_spoken_list(spoken_items)}."
            )
        else:
            base_response = (
                f"У тебя {pluralize_events(count)}. "
                f"Из ближайшего: {join_spoken_list(spoken_items[:5])}."
            )
        if google_sync_error:
            return (
                base_response
                + f"\n\nGoogle Calendar не синхронизирован: {google_sync_error}"
            )
        return base_response

    if intent_result.intent == "delete_event":
        result = get_events()
        events = result["events"]
        target = intent_result.data.get("target", "")
        if not str(target).strip():
            return "Скажи, какое событие удалить. Можно по названию или по номеру из списка."
        resolved = _resolve_event_target(events, target)
        if not resolved:
            return "Не нашла такое событие для удаления. Скажи название точнее или номер из списка."

        deleted = delete_event(resolved["id"])
        if not deleted:
            return "Не удалось удалить событие."
        prefix = pick_variant(
            resolved["title"],
            "Хорошо. Удалил событие:",
            "Готово. Удалил событие:",
            "Сделано. Удалил событие:",
        )
        return f"{prefix} {resolved['title']}."

    return "Не удалось обработать календарную команду."


def _resolve_event_target(events: list[dict], target: str) -> dict | None:
    normalized_target = str(target).strip()
    if not normalized_target:
        return None

    if normalized_target.isdigit():
        index = int(normalized_target) - 1
        if 0 <= index < len(events):
            return events[index]
        return None

    lowered_target = normalized_target.casefold()
    for event in events:
        title = event.get("title", "")
        if title.casefold() == lowered_target:
            return event

    for event in events:
        title = event.get("title", "")
        if lowered_target in title.casefold():
            return event

    return None
