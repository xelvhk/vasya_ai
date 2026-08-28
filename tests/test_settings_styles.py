from __future__ import annotations

import unittest

from scripts.ui.settings_styles import SETTINGS_DIALOG_STYLESHEET


class SettingsStylesTests(unittest.TestCase):
    def test_settings_dialog_stylesheet_keeps_core_selectors(self) -> None:
        self.assertIn("QDialog", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("QTabWidget#settingsTabs::pane", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("QWidget#settingsTabPage", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("QDialogButtonBox QPushButton", SETTINGS_DIALOG_STYLESHEET)

    def test_settings_dialog_stylesheet_uses_accessible_neutral_palette(self) -> None:
        self.assertIn("#0b0b0b", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("#f1f1f1", SETTINGS_DIALOG_STYLESHEET)
        self.assertIn("#b3b3b3", SETTINGS_DIALOG_STYLESHEET)
        self.assertNotIn("#7b3dff", SETTINGS_DIALOG_STYLESHEET)

    def test_settings_dialog_stylesheet_supports_scrollable_tabs(self) -> None:
        self.assertIn("QScrollArea", SETTINGS_DIALOG_STYLESHEET)


if __name__ == "__main__":
    unittest.main()
