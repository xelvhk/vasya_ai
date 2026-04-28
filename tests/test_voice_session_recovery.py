from __future__ import annotations

import unittest

from voice import session
from voice.session import CaptureOutcome


class VoiceSessionRecoveryTests(unittest.TestCase):
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
