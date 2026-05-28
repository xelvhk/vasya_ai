from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Thread
from urllib.parse import quote
from urllib.request import urlopen

from config.settings import (
    AVATAR_STATE_FILE,
    MORNING_SHOW_CITY,
    MORNING_SHOW_ENABLED,
    MORNING_SHOW_HOUR_LIMIT,
    MORNING_SHOW_PREWARM_ENABLED,
    MORNING_SHOW_STATE_FILE,
    MORNING_SHOW_WEATHER_CACHE_MINUTES,
    MEMORY_WIKI_DIR,
)
from services.calendar_service import get_events
from services.memory_center_service import (
    list_memory_daily_digests,
    list_recent_memory_center,
    get_memory_center_status,
)
from services.ollama_client import generate
from services.task_service import get_tasks


@dataclass(frozen=True)
class MorningBriefResult:
    ok: bool
    date: str
    spoken_summary: str
    markdown_path: str | None
    sections: dict
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


_QUOTES: tuple[str, ...] = (
    "Маленький шаг сегодня лучше большого плана на потом.",
    "Спокойный ритм часто быстрее суеты.",
    "Сначала главное, потом остальное.",
    "Последовательность сильнее вдохновения.",
    "Сделай один полезный шаг и день уже удался.",
    "Лучший момент начать это сейчас.",
)


def build_morning_brief(
    now: datetime | None = None,
    *,
    city: str | None = None,
    save_markdown: bool = True,
    use_llm: bool = True,
    weather_timeout: float = 1.2,
    allow_stale_weather: bool = True,
) -> MorningBriefResult:
    current = now or datetime.now()
    day_iso = current.date().isoformat()
    runtime = _load_runtime_config()
    resolved_city = (
        str(city).strip()
        if city is not None
        else str(runtime.get("city", MORNING_SHOW_CITY)).strip()
    ) or MORNING_SHOW_CITY

    sections: dict = {}
    warnings: list[str] = []
    sections["weather"] = _collect_weather_section(
        city=resolved_city,
        weather_timeout=weather_timeout,
        allow_stale_weather=allow_stale_weather,
        warnings=warnings,
    )
    sections["tasks"] = _collect_tasks_section(warnings=warnings)
    sections["events"] = _collect_events_section(today=current.date(), warnings=warnings)
    sections["memory"] = _collect_memory_section(warnings=warnings)
    sections["priorities"] = _build_priority_section(sections)

    spoken_summary = _build_template_spoken_summary(day_iso=day_iso, sections=sections)
    if use_llm:
        llm_summary = _build_llm_spoken_summary(day_iso=day_iso, sections=sections)
        if llm_summary:
            spoken_summary = llm_summary

    markdown_path = None
    if save_markdown:
        try:
            markdown_path = str(_write_morning_brief_markdown(
                day_iso=day_iso,
                spoken_summary=spoken_summary,
                sections=sections,
                warnings=warnings,
            ))
        except Exception as exc:
            warnings.append(f"Markdown-брифинг не удалось сохранить: {exc}")

    return MorningBriefResult(
        ok=True,
        date=day_iso,
        spoken_summary=spoken_summary,
        markdown_path=markdown_path,
        sections=sections,
        warnings=warnings,
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
    prepared = _get_prepared_message(state=state, day_iso=today, city=resolved_city)
    message = prepared
    if not message:
        brief = build_morning_brief(
            current,
            city=resolved_city,
            save_markdown=True,
            use_llm=True,
            weather_timeout=1.2,
            allow_stale_weather=True,
        )
        message = _append_markdown_path_to_summary(brief)
    if not prepared:
        _save_prepared_message(state=state, day_iso=today, city=resolved_city, message=message)

    if mark_delivered:
        state["last_show_date"] = today
        _save_state(state)
    return message


def prewarm_morning_show_async(
    *,
    now: datetime | None = None,
    city: str | None = None,
    hour_limit: int | None = None,
    enabled: bool | None = None,
) -> None:
    if enabled is False:
        return
    if not MORNING_SHOW_PREWARM_ENABLED and enabled is None:
        return
    thread = Thread(
        target=_prewarm_morning_show,
        kwargs={
            "now": now,
            "city": city,
            "hour_limit": hour_limit,
            "enabled": enabled,
        },
        daemon=True,
        name="morning-show-prewarm",
    )
    thread.start()


def get_weather_quick_reply(city: str | None = None) -> str:
    runtime = _load_runtime_config()
    resolved_city = (
        str(city).strip()
        if city is not None
        else str(runtime.get("city", MORNING_SHOW_CITY)).strip()
    ) or MORNING_SHOW_CITY
    state = _load_state()
    weather = _get_cached_weather_line(state=state, city=resolved_city, allow_stale=True)
    if weather:
        return weather

    weather_line = _fetch_weather_line(
        resolved_city,
        timeout=0.9,
    )
    if weather_line:
        _save_cached_weather_line(state=state, city=resolved_city, line=weather_line)
        return weather_line

    return f"По погоде в {resolved_city} сейчас не удалось быстро получить данные. Повтори через пару секунд."


def reset_morning_show_today() -> None:
    state = _load_state()
    if state.pop("last_show_date", None) is not None:
        _save_state(state)


def _quote_for_day(day_iso: str) -> str:
    day_seed = sum(ord(ch) for ch in day_iso)
    return _QUOTES[day_seed % len(_QUOTES)]


def _fetch_weather_line(city: str, *, timeout: float = 1.8) -> str | None:
    city_name = city.strip() or "Moscow"
    url = f"https://wttr.in/{quote(city_name)}?format=j1"
    try:
        with urlopen(url, timeout=max(0.3, timeout)) as response:  # nosec B310
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


def _collect_weather_section(
    *,
    city: str,
    weather_timeout: float,
    allow_stale_weather: bool,
    warnings: list[str],
) -> dict:
    state = _load_state()
    weather_line = _get_cached_weather_line(
        state=state,
        city=city,
        allow_stale=allow_stale_weather,
    )
    if weather_line is None:
        weather_line = _fetch_weather_line(city, timeout=weather_timeout)
        if weather_line:
            _save_cached_weather_line(state=state, city=city, line=weather_line)
            _save_state(state)
    if not weather_line:
        warnings.append(f"Погоду для {city} не удалось получить.")
    return {"city": city, "summary": weather_line or ""}


def _collect_tasks_section(*, warnings: list[str]) -> dict:
    try:
        tasks = list(get_tasks())
    except Exception as exc:
        warnings.append(f"Задачи недоступны: {exc}")
        return {"open_count": 0, "upcoming": []}

    dated = [task for task in tasks if str(task.get("datetime") or "").strip()]
    dated.sort(key=lambda item: str(item.get("datetime") or ""))
    upcoming = [
        {
            "id": task.get("id"),
            "task": str(task.get("task") or "").strip(),
            "datetime": str(task.get("datetime") or "").strip() or None,
        }
        for task in dated[:3]
        if str(task.get("task") or "").strip()
    ]
    return {"open_count": len(tasks), "upcoming": upcoming}


def _collect_events_section(*, today: date, warnings: list[str]) -> dict:
    today_iso = today.isoformat()
    tomorrow_iso = (today + timedelta(days=1)).isoformat()
    try:
        payload = get_events()
    except Exception as exc:
        warnings.append(f"Календарь недоступен: {exc}")
        return {"today": [], "tomorrow": []}

    sync_error = payload.get("google_sync_error") if isinstance(payload, dict) else None
    if sync_error:
        warnings.append(f"Google Calendar: {sync_error}")
    raw_events = payload.get("events") if isinstance(payload, dict) else []
    if not isinstance(raw_events, list):
        raw_events = []
    return {
        "today": _events_for_date(raw_events, today_iso)[:5],
        "tomorrow": _events_for_date(raw_events, tomorrow_iso)[:5],
    }


def _collect_memory_section(*, warnings: list[str]) -> dict:
    status: dict = {}
    recent: dict = {}
    latest_digest: dict = {}
    try:
        status = get_memory_center_status()
    except Exception as exc:
        warnings.append(f"Memory Center status недоступен: {exc}")
    try:
        recent = list_recent_memory_center(limit=5)
    except Exception as exc:
        warnings.append(f"Memory Center recent недоступен: {exc}")
    try:
        latest_digest = list_memory_daily_digests(limit=1)
    except Exception as exc:
        warnings.append(f"Memory digest недоступен: {exc}")

    if isinstance(status, dict):
        sync_connections = status.get("sync_connections")
        if isinstance(sync_connections, list):
            for item in sync_connections:
                if not isinstance(item, dict):
                    continue
                error = str(item.get("last_error") or "").strip()
                if error:
                    toolkit = str(item.get("toolkit") or "source")
                    warnings.append(f"Memory sync {toolkit}: {error}")

    recent_items = recent.get("items") if isinstance(recent, dict) else []
    digest_items = latest_digest.get("items") if isinstance(latest_digest, dict) else []
    return {
        "status": str(status.get("status") or "unknown") if isinstance(status, dict) else "unknown",
        "sources_count": int(status.get("sources_count") or 0) if isinstance(status, dict) else 0,
        "chunks_count": int(status.get("chunks_count") or 0) if isinstance(status, dict) else 0,
        "recent": _compact_memory_items(recent_items if isinstance(recent_items, list) else []),
        "latest_digest": digest_items[0] if isinstance(digest_items, list) and digest_items else None,
    }


def _events_for_date(events: list, day_iso: str) -> list[dict]:
    matched = []
    for event in events:
        if not isinstance(event, dict):
            continue
        dt = str(event.get("datetime") or "").strip()
        if not dt.startswith(day_iso):
            continue
        title = str(event.get("title") or "").strip()
        if title:
            matched.append(
                {
                    "id": event.get("id"),
                    "title": title,
                    "datetime": dt,
                    "source": str(event.get("source") or "local"),
                }
            )
    matched.sort(key=lambda item: str(item.get("datetime") or ""))
    return matched


def _compact_memory_items(items: list) -> list[dict]:
    compact = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        compact.append(
            {
                "title": title,
                "source_key": str(item.get("source_key") or "source"),
                "snippet": _summarize_for_brief(str(item.get("snippet") or ""), limit=120),
                "markdown_path": str(item.get("markdown_path") or "").strip(),
                "url": str(item.get("url") or "").strip(),
            }
        )
    return compact


def _build_priority_section(sections: dict) -> list[str]:
    priorities: list[str] = []
    for task in sections.get("tasks", {}).get("upcoming", []):
        text = str(task.get("task") or "").strip()
        if text:
            priorities.append(f"Закрыть задачу: {text}")
        if len(priorities) >= 3:
            return priorities
    for event in sections.get("events", {}).get("today", []):
        title = str(event.get("title") or "").strip()
        if title:
            priorities.append(f"Подготовиться к событию: {title}")
        if len(priorities) >= 3:
            return priorities
    for item in sections.get("memory", {}).get("recent", []):
        title = str(item.get("title") or "").strip()
        if title:
            priorities.append(f"Просмотреть свежий контекст: {title}")
        if len(priorities) >= 3:
            return priorities

    for item in (
        "Выбрать один главный шаг дня",
        "Разобрать ближайшую открытую задачу",
        "Зафиксировать короткий итог дня в памяти",
    ):
        if len(priorities) >= 3:
            break
        priorities.append(item)
    return priorities


def _build_template_spoken_summary(*, day_iso: str, sections: dict) -> str:
    weather = str(sections.get("weather", {}).get("summary") or "").strip()
    tasks = sections.get("tasks", {})
    events = sections.get("events", {})
    memory = sections.get("memory", {})
    priorities = sections.get("priorities", [])
    first_priority = str(priorities[0] if priorities else "Выбрать один главный шаг дня")

    parts = [f"Доброе утро. Брифинг на {day_iso}."]
    if weather:
        parts.append(weather)
    parts.append(f"Открытых задач: {int(tasks.get('open_count') or 0)}.")
    parts.append(f"Событий сегодня: {len(events.get('today') or [])}.")
    parts.append(f"В Memory Center свежих подсказок: {len(memory.get('recent') or [])}.")
    parts.append(f"Главный фокус: {first_priority}.")
    parts.append(f"Мысль дня: {_quote_for_day(day_iso)}")
    return " ".join(parts)


def _build_llm_spoken_summary(*, day_iso: str, sections: dict) -> str | None:
    prompt = (
        "Собери короткий утренний брифинг на русском в 4-6 предложениях. "
        "Без Markdown, без списков, спокойно и по делу. "
        "Не выдумывай факты, используй только JSON ниже.\n\n"
        f"Дата: {day_iso}\n"
        f"Данные: {json.dumps(sections, ensure_ascii=False)[:6000]}"
    )
    try:
        summary = generate(prompt, temperature=0.2, num_predict=180)
    except Exception:
        return None
    summary = " ".join(summary.split())
    return summary[:900] or None


def _write_morning_brief_markdown(
    *,
    day_iso: str,
    spoken_summary: str,
    sections: dict,
    warnings: list[str],
) -> Path:
    brief_dir = Path(MEMORY_WIKI_DIR).expanduser() / "briefings"
    brief_dir.mkdir(parents=True, exist_ok=True)
    path = brief_dir / f"{day_iso}.md"
    path.write_text(
        _compose_morning_brief_markdown(
            day_iso=day_iso,
            spoken_summary=spoken_summary,
            sections=sections,
            warnings=warnings,
        ),
        encoding="utf-8",
    )
    return path


def _compose_morning_brief_markdown(
    *,
    day_iso: str,
    spoken_summary: str,
    sections: dict,
    warnings: list[str],
) -> str:
    lines = [
        "---",
        "type: morning_brief",
        f"date: {day_iso}",
        "---",
        "",
        f"# Morning Brief {day_iso}",
        "",
        "## Summary",
        "",
        _markdown_line(spoken_summary),
        "",
        "## Weather",
        "",
        _markdown_line(str(sections.get("weather", {}).get("summary") or "_No weather data._")),
        "",
        "## Tasks",
        "",
        f"Open tasks: {int(sections.get('tasks', {}).get('open_count') or 0)}",
        "",
    ]
    _append_task_lines(lines, sections.get("tasks", {}).get("upcoming") or [])
    lines.extend(["", "## Calendar", ""])
    _append_event_lines(lines, "Today", sections.get("events", {}).get("today") or [])
    _append_event_lines(lines, "Tomorrow", sections.get("events", {}).get("tomorrow") or [])
    lines.extend(["", "## Memory Context", ""])
    memory = sections.get("memory", {})
    lines.append(f"Status: {memory.get('status', 'unknown')}")
    lines.append(f"Sources: {memory.get('sources_count', 0)}")
    lines.append(f"Chunks: {memory.get('chunks_count', 0)}")
    latest_digest = memory.get("latest_digest")
    if isinstance(latest_digest, dict):
        lines.append(
            f"Latest digest: {latest_digest.get('date', 'unknown')} "
            f"({latest_digest.get('chunks_count', 0)} chunks)"
        )
        if latest_digest.get("path"):
            lines.append(f"Digest file: {_markdown_line(str(latest_digest.get('path') or ''))}")
    recent = memory.get("recent") or []
    if recent:
        lines.extend(["", "Recent:"])
        for item in recent:
            title = _markdown_line(str(item.get("title") or "Untitled"))
            source_key = _markdown_line(str(item.get("source_key") or "source"))
            lines.append(f"- {title} [{source_key}]")
            if item.get("snippet"):
                lines.append(f"  {_markdown_line(str(item.get('snippet') or ''))}")
    else:
        lines.extend(["", "_No recent memory chunks._"])

    lines.extend(["", "## Suggested Priorities", ""])
    for priority in sections.get("priorities", []) or []:
        lines.append(f"- [ ] {_markdown_line(str(priority))}")
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {_markdown_line(str(warning))}")
    return "\n".join(lines).strip() + "\n"


def _append_task_lines(lines: list[str], tasks: list) -> None:
    if not tasks:
        lines.append("_No dated open tasks._")
        return
    for task in tasks:
        when = _markdown_line(str(task.get("datetime") or "without date"))
        task_text = _markdown_line(str(task.get("task") or "Untitled task"))
        lines.append(f"- [ ] {task_text} ({when})")


def _append_event_lines(lines: list[str], label: str, events: list) -> None:
    lines.append(f"### {label}")
    lines.append("")
    if not events:
        lines.append("_No events._")
        lines.append("")
        return
    for event in events:
        when = _markdown_line(str(event.get("datetime") or "without time"))
        title = _markdown_line(str(event.get("title") or "Untitled event"))
        lines.append(f"- {when}: {title}")
    lines.append("")


def _append_markdown_path_to_summary(brief: MorningBriefResult) -> str:
    if brief.markdown_path:
        return f"{brief.spoken_summary} Полный брифинг: {brief.markdown_path}"
    return brief.spoken_summary


def _summarize_for_brief(value: str, *, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _markdown_line(value: str) -> str:
    text = " ".join(str(value or "").split())
    replacements = {
        "\\": "\\\\",
        "`": "\\`",
        "*": "\\*",
        "_": "\\_",
        "[": "\\[",
        "]": "\\]",
        "(": "\\(",
        ")": "\\)",
        "#": "\\#",
        "<": "\\<",
        ">": "\\>",
    }
    for raw, escaped in replacements.items():
        text = text.replace(raw, escaped)
    return text


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


def _prewarm_morning_show(
    *,
    now: datetime | None = None,
    city: str | None = None,
    hour_limit: int | None = None,
    enabled: bool | None = None,
) -> None:
    runtime = _load_runtime_config()
    resolved_enabled = (
        bool(enabled)
        if enabled is not None
        else bool(runtime.get("enabled", MORNING_SHOW_ENABLED))
    )
    if not resolved_enabled:
        return
    current = now or datetime.now()
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
    if current.hour > resolved_hour_limit:
        return

    resolved_city = (
        str(city).strip()
        if city is not None
        else str(runtime.get("city", MORNING_SHOW_CITY)).strip()
    ) or MORNING_SHOW_CITY
    day_iso = current.date().isoformat()
    state = _load_state()
    if _get_prepared_message(state=state, day_iso=day_iso, city=resolved_city):
        return
    brief = build_morning_brief(
        current,
        city=resolved_city,
        save_markdown=True,
        use_llm=False,
        weather_timeout=0.9,
        allow_stale_weather=True,
    )
    message = _append_markdown_path_to_summary(brief)
    _save_prepared_message(state=state, day_iso=day_iso, city=resolved_city, message=message)
    _save_state(state)


def _get_prepared_message(*, state: dict, day_iso: str, city: str) -> str | None:
    prepared = state.get("prepared_show")
    if not isinstance(prepared, dict):
        return None
    if str(prepared.get("day", "")) != day_iso:
        return None
    if str(prepared.get("city", "")).strip().lower() != city.strip().lower():
        return None
    message = str(prepared.get("message", "")).strip()
    return message or None


def _save_prepared_message(*, state: dict, day_iso: str, city: str, message: str) -> None:
    state["prepared_show"] = {
        "day": day_iso,
        "city": city.strip(),
        "message": message,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _get_cached_weather_line(*, state: dict, city: str, allow_stale: bool) -> str | None:
    weather = state.get("weather_cache")
    if not isinstance(weather, dict):
        return None
    if str(weather.get("city", "")).strip().lower() != city.strip().lower():
        return None
    line = str(weather.get("line", "")).strip()
    if not line:
        return None
    updated_at = _try_parse_iso(str(weather.get("updated_at", "")).strip())
    if updated_at is None:
        return line if allow_stale else None
    age_minutes = (datetime.now() - updated_at).total_seconds() / 60.0
    if age_minutes <= max(1, MORNING_SHOW_WEATHER_CACHE_MINUTES):
        return line
    if allow_stale:
        return line
    return None


def _save_cached_weather_line(*, state: dict, city: str, line: str) -> None:
    state["weather_cache"] = {
        "city": city.strip(),
        "line": line.strip(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _try_parse_iso(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
