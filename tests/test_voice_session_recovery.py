from __future__ import annotations

import unittest
from contextlib import ExitStack
from unittest.mock import patch

from core.orchestrator import ProcessResult
from voice import session
from voice.session import CaptureOutcome


class VoiceSessionRecoveryTests(unittest.TestCase):
    def test_success_and_followup_timeout_record_voice_status(self) -> None:
        for followup in (False, True):
            with self.subTest(followup=followup), ExitStack() as stack:
                stack.enter_context(patch.object(session, "start_runtime_prewarm_async"))
                stack.enter_context(patch.object(session, "get_morning_show_message", return_value=None))
                stack.enter_context(patch.object(session, "_load_runtime_followup_config", return_value={"enabled": True, "listen_seconds": 1, "retries": 1}))
                stack.enter_context(patch.object(session, "_capture_user_text", side_effect=[
                    CaptureOutcome(text="команда", capture_ms=10, last_rms=100),
                    CaptureOutcome(text=None, failure_reason="empty_transcription", capture_ms=20, last_rms=40),
                ]))
                stack.enter_context(patch.object(session, "_try_local_fast_lane", return_value=ProcessResult(
                    intent="get_tasks", response="Готово", needs_followup=followup,
                )))
                stack.enter_context(patch.object(session, "_speak_with_barge_in", return_value=session.BargeInOutcome(None, 4)))
                stack.enter_context(patch.object(session.dictation_mode_store, "is_enabled", return_value=False))
                stack.enter_context(patch.object(session.assistant_state, "set"))
                stack.enter_context(patch.object(session.assistant_control, "consume_action", return_value=None))
                stack.enter_context(patch.object(session.time, "sleep"))
                log_perf = stack.enter_context(patch.object(session, "_log_voice_perf"))
                session.run_voice_interaction()

                values = log_perf.call_args.kwargs
                self.assertEqual(values["status"], "followup_timeout" if followup else "ok")
                self.assertEqual(values["metrics"]["capture_ms"], 30 if followup else 10)
                self.assertEqual(values["failure_reason"], "empty_transcription" if followup else None)

    def test_capture_failure_records_status_and_audio_metrics(self) -> None:
        capture = CaptureOutcome(text=None, failure_reason="device_error", capture_ms=12, stt_ms=3, last_rms=42)
        with ExitStack() as stack:
            stack.enter_context(patch.object(session, "start_runtime_prewarm_async"))
            stack.enter_context(patch.object(session, "get_morning_show_message", return_value=None))
            stack.enter_context(patch.object(session, "_capture_user_text", return_value=capture))
            stack.enter_context(patch.object(session, "speak"))
            stack.enter_context(patch.object(session.assistant_state, "set"))
            stack.enter_context(patch.object(session.assistant_control, "consume_action", return_value=None))
            log_perf = stack.enter_context(patch.object(session, "_log_voice_perf"))
            session.run_voice_interaction()

        values = log_perf.call_args.kwargs
        self.assertEqual(values["status"], "capture_failed")
        self.assertEqual(values["failure_reason"], "device_error")
        self.assertEqual(values["metrics"]["capture_ms"], 12)
        self.assertEqual(values["last_capture_rms"], 42)

    def _bounds(self) -> tuple[float, float]:
        min_good = max(session.MIN_AUDIO_RMS * 1.15, session.MIN_AUDIO_RMS + 25.0)
        max_good = max(1200.0, min_good + 120.0)
        return (min_good, max_good)

    def test_ultra_fast_recovery_enabled_for_good_signal_empty_transcription(self) -> None:
        capture = CaptureOutcome(
            text=None,
            failure_reason="empty_transcription",
            last_rms=max(session.MIN_AUDIO_RMS + 60.0, 180.0),
        )
        self.assertTrue(
            session._should_use_ultra_fast_recovery(
                capture,
                streak=2,
                rms_bounds=self._bounds(),
            )
        )

    def test_ultra_fast_recovery_disabled_for_low_audio(self) -> None:
        capture = CaptureOutcome(
            text=None,
            failure_reason="low_audio_level",
            last_rms=max(1.0, session.MIN_AUDIO_RMS - 5.0),
        )
        self.assertFalse(
            session._should_use_ultra_fast_recovery(
                capture,
                streak=3,
                rms_bounds=self._bounds(),
            )
        )

    def test_ultra_fast_recovery_disabled_for_too_noisy_signal(self) -> None:
        capture = CaptureOutcome(
            text=None,
            failure_reason="empty_transcription",
            last_rms=2000.0,
        )
        self.assertFalse(
            session._should_use_ultra_fast_recovery(
                capture,
                streak=3,
                rms_bounds=self._bounds(),
            )
        )

    def test_ultra_fast_recovery_requires_streak(self) -> None:
        capture = CaptureOutcome(
            text=None,
            failure_reason="empty_transcription",
            last_rms=max(session.MIN_AUDIO_RMS + 70.0, 200.0),
        )
        self.assertFalse(
            session._should_use_ultra_fast_recovery(
                capture,
                streak=1,
                rms_bounds=self._bounds(),
            )
        )


if __name__ == "__main__":
    unittest.main()
