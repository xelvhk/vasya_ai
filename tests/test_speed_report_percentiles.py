from __future__ import annotations

from unittest.mock import patch

from services.speed_report_service import build_voice_speed_report


def test_speed_report_shows_tail_latency_for_user_visible_stages() -> None:
    samples = [
        {"status": "ok", "total_ms": 1000, "capture_ms": 100, "stt_ms": 200,
         "intent_ms": 300, "tts_ms": 400, "first_response_ms": 600,
         "first_action_ms": 500},
        {"status": "ok", "total_ms": 3000, "capture_ms": 500, "stt_ms": 700,
         "intent_ms": 800, "tts_ms": 1000, "first_response_ms": 1500,
         "first_action_ms": 1400},
    ]
    with patch("services.speed_report_service._load_recent_voice_perf", return_value=samples):
        report = build_voice_speed_report(limit=2)
    assert "total p95" in report
    assert "stt p95" in report
    assert "intent p95" in report
    assert "tts p95" in report
    assert "first-response p95" in report
