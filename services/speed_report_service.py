from __future__ import annotations

import json
from pathlib import Path

from config.settings import INTERACTION_LOG_FILE, MIN_AUDIO_RMS, VOICE_SPEED_REPORT_WINDOW


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
    local_fast_lane_values = [int(item.get("local_fast_lane_hits", 0) or 0) for item in samples]
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
    interrupt_profile_distribution = _build_field_distribution(samples, "auto_interrupt_profile")
    routing_profile_distribution = _build_field_distribution(samples, "routing_profile")
    prompt_pack_profile_distribution = _build_field_distribution(samples, "prompt_pack_profile")
    primary_role_distribution = _build_primary_role_distribution(samples)
    primary_intent_distribution = _build_field_distribution(samples, "primary_intent")
    routing_ab_ttfr = _build_ab_latency_summary(samples, "routing_profile", "first_response_ms")
    routing_ab_tta = _build_ab_latency_summary(samples, "routing_profile", "first_action_ms")
    fast_lane_rate = 100.0 * sum(1 for value in local_fast_lane_values if value > 0) / len(samples)

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
    extras.append(f"local fast-lane сессии {fast_lane_rate:.0f}%")
    if any(local_fast_lane_values):
        extras.append(f"local fast-lane avg {_avg(local_fast_lane_values):.2f} на сессию")
    if interrupt_profile_distribution:
        extras.append(f"auto-interrupt профили: {interrupt_profile_distribution}")
    if routing_profile_distribution:
        extras.append(f"routing профили: {routing_profile_distribution}")
    if prompt_pack_profile_distribution:
        extras.append(f"prompt-pack профили: {prompt_pack_profile_distribution}")
    if primary_role_distribution:
        extras.append(f"роли (primary): {primary_role_distribution}")
    if primary_intent_distribution:
        extras.append(f"intents (primary): {primary_intent_distribution}")
    if routing_ab_ttfr:
        extras.append(f"A/B TTFR: {routing_ab_ttfr}")
    if routing_ab_tta:
        extras.append(f"A/B TTA: {routing_ab_tta}")

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


def build_voice_tuning_hints(*, limit: int = 24) -> str:
    samples = _load_recent_voice_perf(limit=max(8, int(limit)))
    if not samples:
        return "Сделай 8-10 голосовых запросов, и я дам рекомендации по ускорению."

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

    hints: list[str] = []
    if p50_ms > 4200:
        hints.append("Скорость: попробуй уменьшить размер ответа модели (num_predict) и длину записи до 2.5-3.0с.")
    elif p50_ms > 2800:
        hints.append("Скорость: можно еще ускорить короткий контур через более агрессивный fast-path для частых фраз.")
    else:
        hints.append("Скорость: контур уже быстрый, лучше фокус на стабильности распознавания.")

    if not_heard_rate >= 25.0:
        hints.append("Распознавание: высокий процент 'не расслышал', проверь уровень микрофона и шум фона.")
    elif not_heard_rate >= 15.0:
        hints.append("Распознавание: умеренный процент 'не расслышал', стоит немного повысить громкость речи.")

    if false_barge_rate >= 30.0:
        hints.append("Barge-in: много ложных срабатываний, увеличь 'подтверждений (шумно)' или порог шумной среды.")
    elif false_barge_rate >= 15.0:
        hints.append("Barge-in: есть ложные срабатывания, можно слегка поднять порог шумной среды.")

    if fail_rate >= 30.0:
        hints.append("Надежность: много неуспешных сессий, стоит перепроверить микрофон и профили STT.")
    elif fail_rate >= 18.0:
        hints.append("Надежность: есть заметные сбои, полезно прогнать тест микрофона в настройках.")

    if not hints:
        hints.append("Метрики в норме: можно продолжать полировать разговорный UX.")

    return "\n".join(hints[:4])


def build_voice_diagnostics_report(*, limit: int = 24) -> str:
    snapshot = build_voice_health_snapshot(limit=limit)
    report = build_voice_speed_report(limit=limit)
    hints = build_voice_tuning_hints(limit=limit)
    return f"{snapshot}\n\n{report}\n\nРекомендации:\n{hints}"


def build_voice_auto_tune_plan(
    *,
    current: dict[str, float | int | bool],
    limit: int = 40,
) -> dict[str, object]:
    samples = _load_recent_voice_perf(limit=max(8, int(limit)))
    if len(samples) < 8:
        return {
            "applied": False,
            "summary": "Нужно минимум 8 голосовых сессий для авто-тюнинга.",
            "sample_count": len(samples),
            "settings": {},
        }

    total_values = [float(item.get("total_ms", 0.0) or 0.0) for item in samples]
    failed_count = sum(1 for item in samples if item.get("status") != "ok")
    not_heard_count = sum(1 for item in samples if bool(item.get("not_heard_failure", False)))
    barge_in_values = [int(item.get("barge_in_count", 0) or 0) for item in samples]
    barge_in_false_values = [int(item.get("barge_in_false_count", 0) or 0) for item in samples]
    followup_timeout_count = sum(1 for item in samples if item.get("status") == "followup_timeout")

    p50_ms = _p50(total_values)
    fail_rate = 100.0 * failed_count / len(samples)
    not_heard_rate = 100.0 * not_heard_count / len(samples)
    timeout_rate = 100.0 * followup_timeout_count / len(samples)
    total_barge_in_count = sum(barge_in_values)
    total_barge_in_false_count = sum(barge_in_false_values)
    false_barge_rate = (
        100.0 * total_barge_in_false_count / total_barge_in_count
        if total_barge_in_count > 0
        else 0.0
    )

    tuned = {
        "smart_followup_enabled": bool(current.get("smart_followup_enabled", True)),
        "smart_followup_listen_seconds": float(current.get("smart_followup_listen_seconds", 3.0)),
        "smart_followup_retries": int(current.get("smart_followup_retries", 1)),
        "auto_interrupt_tts_enabled": bool(current.get("auto_interrupt_tts_enabled", True)),
        "auto_interrupt_sample_seconds": float(current.get("auto_interrupt_sample_seconds", 1.0)),
        "auto_interrupt_adaptive_enabled": bool(current.get("auto_interrupt_adaptive_enabled", True)),
        "auto_interrupt_quiet_rms_threshold": float(current.get("auto_interrupt_quiet_rms_threshold", 140.0)),
        "auto_interrupt_noisy_rms_threshold": float(current.get("auto_interrupt_noisy_rms_threshold", 260.0)),
        "auto_interrupt_hits_quiet": int(current.get("auto_interrupt_hits_quiet", 1)),
        "auto_interrupt_hits_normal": int(current.get("auto_interrupt_hits_normal", 2)),
        "auto_interrupt_hits_noisy": int(current.get("auto_interrupt_hits_noisy", 3)),
    }

    # Надежность: если часто "не расслышал", чуть увеличиваем окно follow-up и количество повторов.
    if not_heard_rate >= 22.0:
        tuned["smart_followup_enabled"] = True
        tuned["smart_followup_listen_seconds"] = min(6.0, tuned["smart_followup_listen_seconds"] + 0.7)
        tuned["smart_followup_retries"] = max(2, tuned["smart_followup_retries"])
        tuned["auto_interrupt_sample_seconds"] = min(1.6, tuned["auto_interrupt_sample_seconds"] + 0.2)
    elif not_heard_rate >= 14.0:
        tuned["smart_followup_listen_seconds"] = min(5.0, tuned["smart_followup_listen_seconds"] + 0.4)
        tuned["smart_followup_retries"] = max(2, tuned["smart_followup_retries"])

    # Ложные прерывания: делаем шумный режим более консервативным.
    if false_barge_rate >= 28.0:
        tuned["auto_interrupt_adaptive_enabled"] = True
        tuned["auto_interrupt_noisy_rms_threshold"] = min(
            520.0,
            tuned["auto_interrupt_noisy_rms_threshold"] + 30.0,
        )
        tuned["auto_interrupt_hits_noisy"] = min(6, tuned["auto_interrupt_hits_noisy"] + 1)
        tuned["auto_interrupt_hits_normal"] = min(5, tuned["auto_interrupt_hits_normal"] + 1)
    elif false_barge_rate >= 16.0:
        tuned["auto_interrupt_adaptive_enabled"] = True
        tuned["auto_interrupt_noisy_rms_threshold"] = min(
            460.0,
            tuned["auto_interrupt_noisy_rms_threshold"] + 15.0,
        )
        tuned["auto_interrupt_hits_noisy"] = min(5, tuned["auto_interrupt_hits_noisy"] + 1)

    # Скорость: если контур медленный и надежность приемлемая, чуть агрессивнее ускоряем.
    if p50_ms >= 4200 and fail_rate <= 20.0 and not_heard_rate <= 18.0:
        tuned["smart_followup_enabled"] = True
        tuned["smart_followup_listen_seconds"] = max(1.8, tuned["smart_followup_listen_seconds"] - 0.5)
        tuned["smart_followup_retries"] = 1
        tuned["auto_interrupt_sample_seconds"] = max(0.8, tuned["auto_interrupt_sample_seconds"] - 0.1)
    elif p50_ms >= 3000 and fail_rate <= 14.0 and not_heard_rate <= 14.0:
        tuned["smart_followup_listen_seconds"] = max(2.2, tuned["smart_followup_listen_seconds"] - 0.3)

    # Если много follow-up timeout, не держим слишком длинное окно.
    if timeout_rate >= 28.0:
        tuned["smart_followup_listen_seconds"] = max(1.8, tuned["smart_followup_listen_seconds"] - 0.4)

    # Нормализация и границы.
    tuned["smart_followup_listen_seconds"] = round(
        min(8.0, max(1.0, float(tuned["smart_followup_listen_seconds"]))),
        1,
    )
    tuned["smart_followup_retries"] = min(3, max(1, int(tuned["smart_followup_retries"])))
    tuned["auto_interrupt_sample_seconds"] = round(
        min(3.0, max(0.5, float(tuned["auto_interrupt_sample_seconds"]))),
        1,
    )
    tuned["auto_interrupt_quiet_rms_threshold"] = round(
        min(600.0, max(50.0, float(tuned["auto_interrupt_quiet_rms_threshold"]))),
        1,
    )
    tuned["auto_interrupt_noisy_rms_threshold"] = round(
        max(
            float(tuned["auto_interrupt_quiet_rms_threshold"]) + 20.0,
            min(900.0, float(tuned["auto_interrupt_noisy_rms_threshold"])),
        ),
        1,
    )
    tuned["auto_interrupt_hits_quiet"] = min(6, max(1, int(tuned["auto_interrupt_hits_quiet"])))
    tuned["auto_interrupt_hits_normal"] = min(6, max(1, int(tuned["auto_interrupt_hits_normal"])))
    tuned["auto_interrupt_hits_noisy"] = min(6, max(1, int(tuned["auto_interrupt_hits_noisy"])))

    changed = {
        key: value
        for key, value in tuned.items()
        if current.get(key) != value
    }
    if not changed:
        return {
            "applied": False,
            "summary": "Авто-тюнинг проверил метрики: текущие значения уже близки к оптимальным.",
            "sample_count": len(samples),
            "settings": tuned,
        }

    summary = (
        f"Авто-тюнинг применён по {len(samples)} сессиям: "
        f"p50 {p50_ms / 1000:.1f}с, не расслышал {not_heard_rate:.0f}%, "
        f"ложные barge-in {false_barge_rate:.0f}%."
    )
    return {
        "applied": True,
        "summary": summary,
        "sample_count": len(samples),
        "settings": tuned,
        "changed": changed,
    }


def derive_ultra_fast_recovery_rms_range(*, limit: int = 80) -> tuple[float, float] | None:
    samples = _load_recent_voice_perf(limit=max(16, int(limit)))
    if len(samples) < 12:
        return None

    good_rms: list[float] = []
    for item in samples:
        if bool(item.get("not_heard_failure", False)):
            continue
        value = item.get("last_capture_rms")
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric <= 0:
            continue
        good_rms.append(numeric)

    if len(good_rms) < 10:
        return None

    p25 = _percentile(good_rms, 0.25)
    p75 = _percentile(good_rms, 0.75)
    min_default = max(MIN_AUDIO_RMS * 1.15, MIN_AUDIO_RMS + 25.0)
    max_default = max(1200.0, min_default + 120.0)

    tuned_min = max(min_default, p25 * 0.85)
    tuned_max = min(1800.0, max(max_default, p75 * 1.25))
    if tuned_max <= tuned_min + 40.0:
        tuned_max = tuned_min + 120.0
    return round(tuned_min, 1), round(tuned_max, 1)


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


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = max(0.0, min(1.0, float(p))) * (len(ordered) - 1)
    lo = int(idx)
    hi = min(len(ordered) - 1, lo + 1)
    frac = idx - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


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


def _build_field_distribution(samples: list[dict], field: str) -> str:
    counts: dict[str, int] = {}
    for item in samples:
        raw_value = item.get(field)
        value = str(raw_value).strip() if raw_value is not None else ""
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return ""
    chunks: list[str] = []
    total = len(samples)
    for value, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        rate = 100.0 * count / total
        chunks.append(f"{value} {count} ({rate:.0f}%)")
    return ", ".join(chunks)


def _build_primary_role_distribution(samples: list[dict]) -> str:
    counts: dict[str, int] = {}
    for item in samples:
        role = str(item.get("primary_role", "")).strip()
        if role:
            counts[role] = counts.get(role, 0) + 1

        role_counts_payload = item.get("role_counts")
        if not isinstance(role_counts_payload, dict):
            continue
        for raw_role, raw_count in role_counts_payload.items():
            role_name = str(raw_role).strip()
            if not role_name:
                continue
            try:
                numeric_count = int(raw_count)
            except (TypeError, ValueError):
                continue
            if numeric_count <= 0:
                continue
            counts[role_name] = counts.get(role_name, 0) + numeric_count

    if not counts:
        return ""
    total = sum(counts.values())
    chunks: list[str] = []
    for role_name, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        rate = 100.0 * count / total if total > 0 else 0.0
        chunks.append(f"{role_name} {count} ({rate:.0f}%)")
    return ", ".join(chunks)


def _build_ab_latency_summary(samples: list[dict], profile_key: str, metric_key: str) -> str:
    buckets: dict[str, list[float]] = {}
    for item in samples:
        profile = str(item.get(profile_key, "")).strip()
        if not profile:
            continue
        metric = item.get(metric_key)
        try:
            metric_value = float(metric)
        except (TypeError, ValueError):
            continue
        if metric_value <= 0:
            continue
        buckets.setdefault(profile, []).append(metric_value)

    if len(buckets) < 2:
        return ""

    parts: list[str] = []
    for profile, values in sorted(
        buckets.items(),
        key=lambda pair: (_avg(pair[1]), pair[0]),
    ):
        parts.append(f"{profile} p50 {_p50(values):.0f}мс (n={len(values)})")
    return ", ".join(parts)
