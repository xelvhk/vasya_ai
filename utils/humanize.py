from __future__ import annotations

from datetime import datetime, timedelta


_MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}
_WEEKDAYS = {
    0: "в понедельник",
    1: "во вторник",
    2: "в среду",
    3: "в четверг",
    4: "в пятницу",
    5: "в субботу",
    6: "в воскресенье",
}


def humanize_event_datetime(dt_text: str | None, now: datetime | None = None) -> str | None:
    if not dt_text:
        return None

    try:
        parsed = datetime.strptime(dt_text, "%Y-%m-%d %H:%M")
    except ValueError:
        return dt_text

    current_time = now or datetime.now()
    target_date = parsed.date()
    current_date = current_time.date()

    if parsed.hour == 0 and parsed.minute == 0:
        time_suffix = ""
    else:
        time_suffix = f" в {parsed.strftime('%H:%M')}"

    if target_date == current_date:
        return f"сегодня{time_suffix}"
    if target_date == current_date + timedelta(days=1):
        return f"завтра{time_suffix}"
    if target_date == current_date + timedelta(days=2):
        return f"послезавтра{time_suffix}"

    if 0 < (target_date - current_date).days < 7:
        return f"{_WEEKDAYS[target_date.weekday()]}{time_suffix}"

    if parsed.year == current_time.year:
        return f"{parsed.day} {_MONTHS[parsed.month]}{time_suffix}"

    return f"{parsed.day} {_MONTHS[parsed.month]} {parsed.year} года{time_suffix}"
