from __future__ import annotations

import unittest
from unittest.mock import patch

from services.speed_report_service import derive_ultra_fast_recovery_rms_range


class SpeedReportRmsRangeTests(unittest.TestCase):
    def test_derive_ultra_fast_recovery_rms_range_returns_none_for_small_sample(self) -> None:
        with patch("services.speed_report_service._load_recent_voice_perf", return_value=[]):
            self.assertIsNone(derive_ultra_fast_recovery_rms_range(limit=20))

    def test_derive_ultra_fast_recovery_rms_range_builds_range_from_good_sessions(self) -> None:
        samples = []
        for rms in (180.0, 190.0, 200.0, 210.0, 220.0, 230.0, 240.0, 250.0, 260.0, 280.0, 300.0, 320.0):
            samples.append(
                {
                    "event_type": "voice_perf",
                    "not_heard_failure": False,
                    "last_capture_rms": rms,
                }
            )
        with patch("services.speed_report_service._load_recent_voice_perf", return_value=samples):
            result = derive_ultra_fast_recovery_rms_range(limit=80)

        self.assertIsNotNone(result)
        assert result is not None
        min_rms, max_rms = result
        self.assertGreaterEqual(min_rms, 0.0)
        self.assertGreater(max_rms, min_rms)
        self.assertGreaterEqual(min_rms, 120.0)


if __name__ == "__main__":
    unittest.main()
