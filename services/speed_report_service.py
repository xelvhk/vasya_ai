from __future__ import annotations

import json
from pathlib import Path

from config.settings import INTERACTION_LOG_FILE, VOICE_SPEED_REPORT_WINDOW


def build_voice_speed_report(*, limit: int | None = None) -> str:
    window = max(5, int(limit if isinstance(limit, int) else VOICE_SPEED_REPORT_WINDOW))
    samples = _load_recent_voice_perf(limit=window)
    if not samples:
        return "Пока нет данных по скорости. Сделай пару голосовых запросов и повтори."

    total_values = [item.get("total_ms", 0.0) for item in samples]
    capture_values = [item.get("capture_ms", 0.0) for item in samples]
    stt_values = [item.get("stt_ms", 0.0) for item in samples]
    intent_values = [item.get("intent_ms", 0.0) for item in samples]
    tts_values = [item.get("tts_ms", 0.0) for item in samples]

    return (
        f"Скорость по последним {len(samples)} запросам: "
        f"total avg {_avg(total_values):.0f} мс, p50 {_p50(total_values):.0f} мс; "
        f"capture avg {_avg(capture_values):.0f} мс; "
        f"stt avg {_avg(stt_values):.0f} мс; "
        f"intent avg {_avg(intent_values):.0f} мс; "
        f"tts avg {_avg(tts_values):.0f} мс."
    )


def _load_recent_voice_perf(*, limit: int) -> list[dict]:
    path = Path(INTERACTION_LOG_FILE)
    if not path.exists():
        return []

    items: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("event_type") != "voice_perf":
            continue
        items.append(payload)
        if len(items) >= limit:
            break
    items.reverse()
    return items


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _p50(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0
