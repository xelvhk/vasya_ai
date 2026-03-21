from __future__ import annotations

import re
from datetime import datetime, timedelta

try:
    import dateparser
except ImportError:  # pragma: no cover - optional dependency
    dateparser = None


DEFAULT_TIME = "09:00"

_TIME_WITH_MINUTES_PATTERN = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_TIME_WITH_PREFIX_PATTERN = re.compile(r"\b(?:в|к)\s+(\d{1,2})(?::(\d{2}))?\b")
_AFTER_DAYS_PATTERN = re.compile(r"\bчерез\s+(\d+)\s+д(?:ень|ня|ней)\b")
_DAY_MONTH_PATTERN = re.compile(
    r"\b(\d{1,2})\s+"
    r"(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b"
)

_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}
_WEEKDAYS = {
    "понедельник": 0,
    "вторник": 1,
    "среду": 2,
    "среда": 2,
    "четверг": 3,
    "пятницу": 4,
    "пятница": 4,
    "субботу": 5,
    "суббота": 5,
    "воскресенье": 6,
}


def normalize_datetime(dt_text: str | None, now: datetime | None = None) -> str | None:
    if not dt_text:
        return None

    cleaned_text = _clean_datetime_text(dt_text)
    if not cleaned_text:
        return None

    current_time = now or datetime.now()

    explicit_result = _parse_common_relative_phrases(cleaned_text, current_time)
    if explicit_result:
        return explicit_result

    built_in_result = _parse_common_absolute_phrases(cleaned_text, current_time)
    if built_in_result:
        return built_in_result

    fallback_result = _parse_with_dateparser(cleaned_text, current_time)
    if fallback_result:
        return fallback_result

    return None


def _clean_datetime_text(dt_text: str) -> str:
    return " ".join(dt_text.strip().lower().split())


def _parse_common_relative_phrases(dt_text: str, now: datetime) -> str | None:
    day_offset = None

    if "послезавтра" in dt_text:
        day_offset = 2
    elif "завтра" in dt_text:
        day_offset = 1
    elif "сегодня" in dt_text:
        day_offset = 0
    else:
        match = _AFTER_DAYS_PATTERN.search(dt_text)
        if match:
            day_offset = int(match.group(1))

    if day_offset is None:
        return None

    base_date = (now + timedelta(days=day_offset)).date()
    hours, minutes = _extract_time(dt_text)
    return _format_datetime(base_date, hours, minutes)


def _parse_with_dateparser(dt_text: str, now: datetime) -> str | None:
    if dateparser is None:
        return None

    parsed = dateparser.parse(
        dt_text,
        languages=["ru"],
        settings={
            "RELATIVE_BASE": now,
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": "Europe/Moscow",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )
    if parsed is None:
        return None

    hours, minutes = _extract_time(dt_text)
    if hours is None or minutes is None:
        hours = parsed.hour
        minutes = parsed.minute

    if hours == 0 and minutes == 0 and not _has_explicit_time(dt_text):
        hours, minutes = map(int, DEFAULT_TIME.split(":"))

    return parsed.replace(hour=hours, minute=minutes, second=0, microsecond=0).strftime(
        "%Y-%m-%d %H:%M"
    )


def _extract_time(dt_text: str) -> tuple[int | None, int | None]:
    match = _TIME_WITH_MINUTES_PATTERN.search(dt_text)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        if hours > 23 or minutes > 59:
            return None, None
        return hours, minutes

    match = _TIME_WITH_PREFIX_PATTERN.search(dt_text)
    if not match:
        return None, None

    hours = int(match.group(1))
    minutes = int(match.group(2) or "00")
    if hours > 23 or minutes > 59:
        return None, None

    return hours, minutes


def _has_explicit_time(dt_text: str) -> bool:
    hours, minutes = _extract_time(dt_text)
    return hours is not None and minutes is not None


def _format_datetime(base_date, hours: int | None, minutes: int | None) -> str:
    if hours is None or minutes is None:
        hours, minutes = map(int, DEFAULT_TIME.split(":"))

    normalized = datetime.combine(
        base_date,
        datetime.min.time(),
    ).replace(hour=hours, minute=minutes)
    return normalized.strftime("%Y-%m-%d %H:%M")


def _parse_common_absolute_phrases(dt_text: str, now: datetime) -> str | None:
    date_match = _DAY_MONTH_PATTERN.search(dt_text)
    if date_match:
        day = int(date_match.group(1))
        month = _MONTHS[date_match.group(2)]
        year = now.year

        try:
            candidate = datetime(year=year, month=month, day=day)
        except ValueError:
            return None

        if candidate.date() < now.date():
            try:
                candidate = candidate.replace(year=year + 1)
            except ValueError:
                return None

        hours, minutes = _extract_time(dt_text)
        return _format_datetime(candidate.date(), hours, minutes)

    for weekday_text, weekday_index in _WEEKDAYS.items():
        if weekday_text in dt_text:
            days_ahead = (weekday_index - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            target_date = (now + timedelta(days=days_ahead)).date()
            hours, minutes = _extract_time(dt_text)
            return _format_datetime(target_date, hours, minutes)

    return None
