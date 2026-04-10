from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from config.settings import (
    AVATAR_STATE_FILE,
    MORNING_SHOW_CITY,
    MORNING_SHOW_ENABLED,
    MORNING_SHOW_HOUR_LIMIT,
    MORNING_SHOW_STATE_FILE,
)
from services.task_service import count_open_tasks


_QUOTES: tuple[str, ...] = (
    "Маленький шаг сегодня лучше большого плана на потом.",
    "Спокойный ритм часто быстрее суеты.",
    "Сначала главное, потом остальное.",
    "Последовательность сильнее вдохновения.",
    "Сделай один полезный шаг и день уже удался.",
    "Лучший момент начать это сейчас.",
)


def get_morning_show_message(
    now: datetime | None = None,
    *,
    force: bool = False,
    city: str | None = None,
    hour_limit: int | None = None,
    enabled: bool | None = None,
    mark_delivered: bool = True,
) -> str | None:
    runtime = _load_runtime_config()
    resolved_enabled = (
        bool(enabled)
        if enabled is not None
        else bool(runtime.get("enabled", MORNING_SHOW_ENABLED))
    )
    resolved_city = (
        str(city).strip()
        if city is not None
        else str(runtime.get("city", MORNING_SHOW_CITY)).strip()
    ) or MORNING_SHOW_CITY
    raw_hour_limit = (
        hour_limit
        if hour_limit is not None
        else runtime.get("hour_limit", MORNING_SHOW_HOUR_LIMIT)
    )
    try:
        resolved_hour_limit = int(raw_hour_limit)
    except (TypeError, ValueError):
        resolved_hour_limit = int(MORNING_SHOW_HOUR_LIMIT)
    resolved_hour_limit = min(23, max(0, resolved_hour_limit))

    if not force and not resolved_enabled:
        return None

    current = now or datetime.now()
    if not force and current.hour > resolved_hour_limit:
        return None

    today = current.date().isoformat()
    state = _load_state()
    if not force and state.get("last_show_date") == today:
        return None

    weather_line = _fetch_weather_line(resolved_city)
    tasks_line = _build_tasks_line()
    quote = _quote_for_day(today)
    parts = ["Доброе утро. Короткое утреннее шоу."]
    if weather_line:
        parts.append(weather_line)
    if tasks_line:
        parts.append(tasks_line)
    parts.append(f"Мысль дня: {quote}")
    message = " ".join(parts)

    if mark_delivered:
        state["last_show_date"] = today
        _save_state(state)
    return message


def reset_morning_show_today() -> None:
    state = _load_state()
    if state.pop("last_show_date", None) is not None:
        _save_state(state)


def _quote_for_day(day_iso: str) -> str:
    day_seed = sum(ord(ch) for ch in day_iso)
    return _QUOTES[day_seed % len(_QUOTES)]


def _fetch_weather_line(city: str) -> str | None:
    city_name = city.strip() or "Moscow"
    url = f"https://wttr.in/{quote(city_name)}?format=j1"
    try:
        with urlopen(url, timeout=1.8) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None

    current = payload.get("current_condition")
    if not isinstance(current, list) or not current:
        return None
    entry = current[0] if isinstance(current[0], dict) else {}
    temp_c = str(entry.get("temp_C", "")).strip()
    feels_like = str(entry.get("FeelsLikeC", "")).strip()
    desc_block = entry.get("weatherDesc")
    desc = ""
    if isinstance(desc_block, list) and desc_block and isinstance(desc_block[0], dict):
        desc = str(desc_block[0].get("value", "")).strip()

    if temp_c and feels_like and desc:
        return f"Погода в {city_name}: {desc}, {temp_c}°C, ощущается как {feels_like}°C."
    if temp_c and desc:
        return f"Погода в {city_name}: {desc}, {temp_c}°C."
    return None


def _build_tasks_line() -> str | None:
    try:
        open_tasks = int(count_open_tasks())
    except Exception:
        return None
    if open_tasks <= 0:
        return "По задачам: открытых задач сейчас нет."
    if open_tasks == 1:
        return "По задачам: открыта 1 задача."
    if 2 <= open_tasks <= 4:
        return f"По задачам: открыто {open_tasks} задачи."
    return f"По задачам: открыто {open_tasks} задач."


def _load_state() -> dict:
    path = Path(MORNING_SHOW_STATE_FILE)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_runtime_config() -> dict:
    path = Path(AVATAR_STATE_FILE)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        "enabled": payload.get("morning_show_enabled", MORNING_SHOW_ENABLED),
        "city": payload.get("morning_show_city", MORNING_SHOW_CITY),
        "hour_limit": payload.get("morning_show_hour_limit", MORNING_SHOW_HOUR_LIMIT),
    }


def _save_state(payload: dict) -> None:
    path = Path(MORNING_SHOW_STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        return
