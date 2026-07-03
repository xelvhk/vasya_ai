from __future__ import annotations

import unittest

from scripts.ui.settings_styles import SETTINGS_DIALOG_STYLESHEET


class SettingsStylesTests(unittest.TestCase):
    def test_settings_dialog_stylesheet_keeps_core_selectors(self) -> None:
        self.assertIn("QDialog", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("QTabWidget#settingsTabs::pane", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("QWidget#settingsTabPage", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("QDialogButtonBox QPushButton", SETTINGS_DIALOG_STYLESHEET)

    def test_settings_dialog_stylesheet_keeps_brand_colors(self) -> None:
        self.assertIn("#070b1f", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("#7b3dff", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("#22b8ff", SETTINGS_DIALOG_STYLESHEET)


if __name__ == "__main__":
    unittest.main()
