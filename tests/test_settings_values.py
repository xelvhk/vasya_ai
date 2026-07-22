from __future__ import annotations

import unittest

from scripts.ui.settings_values import (
    applied_noisy_rms_threshold,
    minimum_noisy_rms_threshold,
)


class SettingsValuesTests(unittest.TestCase):
    def test_minimum_noisy_rms_threshold_keeps_live_sync_gap(self) -> None:
        self.assertEqual(minimum_noisy_rms_threshold(140.0), 160.0)

    def test_applied_noisy_rms_threshold_only_adjusts_when_noisy_is_not_above_quiet(self) -> None:
        self.assertEqual(applied_noisy_rms_threshold(140.0, 140.0), 160.0)
        self.assertEqual(applied_noisy_rms_threshold(140.0, 130.0), 160.0)
        self.assertEqual(applied_noisy_rms_threshold(140.0, 150.0), 150.0)


if __name__ == "__main__":
    unittest.main()
