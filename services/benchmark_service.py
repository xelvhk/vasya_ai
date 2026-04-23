from __future__ import annotations

import json
from pathlib import Path

from config.settings import INTERACTION_LOG_FILE


def build_benchmark_snapshot(*, limit: int = 80) -> dict[str, object]:
    rows = _load_recent_interactions(limit=max(10, int(limit)))
    voice_perf = [row for row in rows if row.get("event_type") == "voice_perf"]
    pipeline_perf = [row for row in rows if row.get("event_type") == "pipeline_text_perf"]

    result: dict[str, object] = {
        "sample_count": len(rows),
        "voice_perf_count": len(voice_perf),
        "pipeline_perf_count": len(pipeline_perf),
    }

    if voice_perf:
        ttfr = _collect_metric(voice_perf, "first_response_ms")
        tta = _collect_metric(voice_perf, "first_action_ms")
        stt = _collect_metric(voice_perf, "stt_ms")
        total = _collect_metric(voice_perf, "total_ms")
        barge = _collect_metric(voice_perf, "barge_in_count")
        false_barge = _collect_metric(voice_perf, "barge_in_false_count")
        not_heard = sum(1 for item in voice_perf if bool(item.get("not_heard_failure", False)))
        result["voice"] = {
            "ttfr_avg_ms": _avg(ttfr),
            "tta_avg_ms": _avg(tta),
            "stt_avg_ms": _avg(stt),
            "total_avg_ms": _avg(total),
            "barge_in_avg": _avg(barge),
            "false_barge_rate_pct": round(
                (sum(false_barge) / max(1.0, sum(barge))) * 100.0,
                2,
            ),
            "not_heard_rate_pct": round((not_heard / max(1, len(voice_perf))) * 100.0, 2),
        }

    if pipeline_perf:
        p_ttfr = _collect_metric(pipeline_perf, "ttfr_ms")
        p_intent = _collect_metric(pipeline_perf, "intent_ms")
        p_total = _collect_metric(pipeline_perf, "total_ms")
        result["pipeline"] = {
            "ttfr_avg_ms": _avg(p_ttfr),
            "intent_avg_ms": _avg(p_intent),
            "total_avg_ms": _avg(p_total),
        }

    return result


def build_benchmark_text_report(*, limit: int = 80) -> str:
    snap = build_benchmark_snapshot(limit=limit)
    voice = snap.get("voice")
    pipeline = snap.get("pipeline")
    if not isinstance(voice, dict) and not isinstance(pipeline, dict):
        return "Недостаточно данных для benchmark. Сделай несколько голосовых запросов."

    lines: list[str] = [
        f"Benchmark snapshot: samples={snap.get('sample_count', 0)}, "
        f"voice={snap.get('voice_perf_count', 0)}, pipeline={snap.get('pipeline_perf_count', 0)}",
    ]
    if isinstance(voice, dict):
        lines.append(
            "Voice: "
            f"TTFR avg {voice.get('ttfr_avg_ms', 0.0):.0f} ms, "
            f"TTA avg {voice.get('tta_avg_ms', 0.0):.0f} ms, "
            f"STT avg {voice.get('stt_avg_ms', 0.0):.0f} ms, "
            f"Total avg {voice.get('total_avg_ms', 0.0):.0f} ms, "
            f"false barge {voice.get('false_barge_rate_pct', 0.0):.1f}%, "
            f"not-heard {voice.get('not_heard_rate_pct', 0.0):.1f}%."
        )
    if isinstance(pipeline, dict):
        lines.append(
            "Pipeline: "
            f"TTFR avg {pipeline.get('ttfr_avg_ms', 0.0):.0f} ms, "
            f"intent avg {pipeline.get('intent_avg_ms', 0.0):.0f} ms, "
            f"total avg {pipeline.get('total_avg_ms', 0.0):.0f} ms."
        )
    return "\n".join(lines)


def _load_recent_interactions(limit: int) -> list[dict]:
    path = Path(INTERACTION_LOG_FILE)
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows[-limit:]


def _collect_metric(rows: list[dict], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)
