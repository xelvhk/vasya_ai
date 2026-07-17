from __future__ import annotations

import unittest

try:
    from scripts.ui.settings_dialog import SettingsDialog
except ImportError:  # pragma: no cover - depends on optional desktop deps
    SettingsDialog = None


@unittest.skipUnless(SettingsDialog is not None, "PySide6 is not installed")
class SettingsDialogTests(unittest.TestCase):
    def test_settings_dialog_exposes_apply_api(self) -> None:
        self.assertTrue(callable(SettingsDialog.apply))


if __name__ == "__main__":
    unittest.main()
