from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

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
_TIME_OF_DAY = {
    "утром": (9, 0),
    "днем": (14, 0),
    "днём": (14, 0),
    "вечером": (19, 0),
    "ночью": (22, 0),
}
_AMBIGUOUS_PHRASES = {
    "на следующей неделе": (
        "Фраза с датой слишком расплывчатая. Лучше сказать, например: "
        "во вторник в 15:00 или в пятницу вечером."
    ),
    "на выходных": (
        "Непонятно, в какой именно день выходных. Лучше назвать конкретный день и время."
    ),
    "в выходные": (
        "Непонятно, в какой именно день выходных. Лучше назвать конкретный день и время."
    ),
    "на неделе": "Непонятно, в какой именно день недели назначить событие.",
    "потом": "Дата не распознана: фраза слишком неопределенная.",
    "позже": "Дата не распознана: фраза слишком неопределенная.",
    "скоро": "Дата не распознана: фраза слишком неопределенная.",
    "как-нибудь": "Дата не распознана: фраза слишком неопределенная.",
}


@dataclass(frozen=True)
class DatetimeParseResult:
    normalized: str | None
    status: Literal["parsed", "parsed_with_default_time", "ambiguous", "unrecognized"]
    message: str | None = None


def parse_datetime(dt_text: str | None, now: datetime | None = None) -> DatetimeParseResult:
    if not dt_text:
        return DatetimeParseResult(normalized=None, status="unrecognized")

    cleaned_text = _clean_datetime_text(dt_text)
    if not cleaned_text:
        return DatetimeParseResult(normalized=None, status="unrecognized")

    ambiguous_message = _get_ambiguous_message(cleaned_text)
    if ambiguous_message:
        return DatetimeParseResult(
            normalized=None,
            status="ambiguous",
            message=ambiguous_message,
        )

    current_time = now or datetime.now()

    for parser in (
        _parse_common_relative_phrases,
        _parse_common_absolute_phrases,
        _parse_with_dateparser,
    ):
        result = parser(cleaned_text, current_time)
        if result:
            return result

    return DatetimeParseResult(normalized=None, status="unrecognized")


def normalize_datetime(dt_text: str | None, now: datetime | None = None) -> str | None:
    return parse_datetime(dt_text, now=now).normalized


def _clean_datetime_text(dt_text: str) -> str:
    return " ".join(dt_text.strip().lower().split())


def _get_ambiguous_message(dt_text: str) -> str | None:
    for phrase, message in _AMBIGUOUS_PHRASES.items():
        if phrase in dt_text:
            return message
    return None


def _parse_common_relative_phrases(
    dt_text: str, now: datetime
) -> DatetimeParseResult | None:
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

    target_date = (now + timedelta(days=day_offset)).date()
    return _build_parse_result(target_date, dt_text)


def _parse_common_absolute_phrases(
    dt_text: str, now: datetime
) -> DatetimeParseResult | None:
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

        return _build_parse_result(candidate.date(), dt_text)

    for weekday_text, weekday_index in _WEEKDAYS.items():
        if weekday_text in dt_text:
            days_ahead = (weekday_index - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            target_date = (now + timedelta(days=days_ahead)).date()
            return _build_parse_result(target_date, dt_text)

    return None


def _parse_with_dateparser(dt_text: str, now: datetime) -> DatetimeParseResult | None:
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

    return _build_parse_result(parsed.date(), dt_text)


def _build_parse_result(base_date: date, dt_text: str) -> DatetimeParseResult:
    hours, minutes, used_default_time = _resolve_time(dt_text)
    normalized = datetime.combine(base_date, datetime.min.time()).replace(
        hour=hours,
        minute=minutes,
    )

    if used_default_time:
        return DatetimeParseResult(
            normalized=normalized.strftime("%Y-%m-%d %H:%M"),
            status="parsed_with_default_time",
            message=f"Время не указано, поэтому поставил {DEFAULT_TIME}.",
        )

    return DatetimeParseResult(
        normalized=normalized.strftime("%Y-%m-%d %H:%M"),
        status="parsed",
    )


def _resolve_time(dt_text: str) -> tuple[int, int, bool]:
    explicit_time = _extract_explicit_time(dt_text)
    if explicit_time != (None, None):
        return explicit_time[0], explicit_time[1], False

    part_of_day_time = _extract_time_of_day(dt_text)
    if part_of_day_time is not None:
        return part_of_day_time[0], part_of_day_time[1], False

    default_hours, default_minutes = map(int, DEFAULT_TIME.split(":"))
    return default_hours, default_minutes, True


def _extract_explicit_time(dt_text: str) -> tuple[int | None, int | None]:
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


def _extract_time_of_day(dt_text: str) -> tuple[int, int] | None:
    for phrase, time_value in _TIME_OF_DAY.items():
        if phrase in dt_text:
            return time_value
    return None
