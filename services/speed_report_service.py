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
    first_action_values = _collect_positive_metric(samples, "first_action_ms")
    first_response_values = _collect_positive_metric(samples, "first_response_ms")
    barge_in_values = [int(item.get("barge_in_count", 0) or 0) for item in samples]
    barge_in_false_values = [int(item.get("barge_in_false_count", 0) or 0) for item in samples]
    followup_timeout_count = sum(1 for item in samples if item.get("status") == "followup_timeout")
    failed_count = sum(1 for item in samples if item.get("status") != "ok")
    not_heard_count = sum(1 for item in samples if bool(item.get("not_heard_failure", False)))
    barge_in_sessions = sum(1 for value in barge_in_values if value > 0)
    total_barge_in_count = sum(barge_in_values)
    total_barge_in_false_count = sum(barge_in_false_values)
    timeout_rate = 100.0 * followup_timeout_count / len(samples)
    fail_rate = 100.0 * failed_count / len(samples)
    barge_in_rate = 100.0 * barge_in_sessions / len(samples)
    not_heard_rate = 100.0 * not_heard_count / len(samples)
    false_barge_rate = (
        100.0 * total_barge_in_false_count / total_barge_in_count
        if total_barge_in_count > 0
        else 0.0
    )
    profile_distribution = _build_profile_distribution(samples)

    base = (
        f"Скорость по последним {len(samples)} запросам: "
        f"total avg {_avg(total_values):.0f} мс, p50 {_p50(total_values):.0f} мс; "
        f"capture avg {_avg(capture_values):.0f} мс; "
        f"stt avg {_avg(stt_values):.0f} мс; "
        f"intent avg {_avg(intent_values):.0f} мс; "
        f"tts avg {_avg(tts_values):.0f} мс."
    )
    extras: list[str] = []
    if first_action_values:
        extras.append(
            f"first-action avg {_avg(first_action_values):.0f} мс, p50 {_p50(first_action_values):.0f} мс"
        )
    if first_response_values:
        extras.append(
            f"first-response avg {_avg(first_response_values):.0f} мс, p50 {_p50(first_response_values):.0f} мс"
        )
    extras.append(f"follow-up timeout {timeout_rate:.0f}%")
    extras.append(f"неуспешные сессии {fail_rate:.0f}%")
    extras.append(f"не расслышал {not_heard_rate:.0f}%")
    extras.append(f"barge-in сессии {barge_in_rate:.0f}%")
    if any(barge_in_values):
        extras.append(f"barge-in avg {_avg(barge_in_values):.2f} на сессию")
        extras.append(f"ложные barge-in {false_barge_rate:.0f}%")
    if profile_distribution:
        extras.append(f"A/B профиль: {profile_distribution}")

    return f"{base} Дополнительно: " + "; ".join(extras) + "."


def build_voice_health_snapshot(*, limit: int = 24) -> str:
    samples = _load_recent_voice_perf(limit=max(8, int(limit)))
    if not samples:
        return "Скорость: пока нет данных"

    total_values = [float(item.get("total_ms", 0.0) or 0.0) for item in samples]
    failed_count = sum(1 for item in samples if item.get("status") != "ok")
    not_heard_count = sum(1 for item in samples if bool(item.get("not_heard_failure", False)))
    barge_in_values = [int(item.get("barge_in_count", 0) or 0) for item in samples]
    barge_in_false_values = [int(item.get("barge_in_false_count", 0) or 0) for item in samples]

    p50_ms = _p50(total_values)
    fail_rate = 100.0 * failed_count / len(samples)
    not_heard_rate = 100.0 * not_heard_count / len(samples)
    total_barge_in_count = sum(barge_in_values)
    total_barge_in_false_count = sum(barge_in_false_values)
    false_barge_rate = (
        100.0 * total_barge_in_false_count / total_barge_in_count
        if total_barge_in_count > 0
        else 0.0
    )

    if fail_rate <= 10.0 and p50_ms <= 2600:
        grade = "Быстро и стабильно"
    elif fail_rate <= 20.0 and p50_ms <= 4200:
        grade = "Нормально"
    else:
        grade = "Нужно подтюнить"

    return (
        f"{grade}: p50 {p50_ms / 1000:.1f}с, "
        f"не расслышал {not_heard_rate:.0f}%, "
        f"ложные barge-in {false_barge_rate:.0f}%"
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


def _collect_positive_metric(samples: list[dict], key: str) -> list[float]:
    values: list[float] = []
    for item in samples:
        value = item.get(key)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric > 0:
            values.append(numeric)
    return values


def _build_profile_distribution(samples: list[dict]) -> str:
    counts: dict[str, int] = {}
    for item in samples:
        raw_profile = item.get("auto_interrupt_profile")
        profile = str(raw_profile).strip() if raw_profile is not None else ""
        if not profile:
            continue
        counts[profile] = counts.get(profile, 0) + 1
    if not counts:
        return ""
    chunks: list[str] = []
    total = len(samples)
    for profile, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        rate = 100.0 * count / total
        chunks.append(f"{profile} {count} ({rate:.0f}%)")
    return ", ".join(chunks)
