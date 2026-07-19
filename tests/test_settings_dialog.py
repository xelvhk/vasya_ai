from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QWidget

    from scripts.ui.settings_dialog import SettingsDialog
except ImportError:  # pragma: no cover - depends on optional desktop deps
    QApplication = None
    SettingsDialog = None
    QWidget = object


class FakeAvatarWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._settings_focus = None
        self._avatar_size = 210
        self._avatar_skin = "classic"
        self._avatar_opacity = 1.0
        self._avatar_path = None
        self._auto_child_skin = True
        self._idle_motion_enabled = False
        self._tray_click_action = "toggle"
        self._show_response_bubble = True
        self._morning_show_enabled = False
        self._morning_show_city = "Moscow"
        self._morning_show_hour_limit = 11
        self._smart_followup_enabled = True
        self._smart_followup_listen_seconds = 3.0
        self._smart_followup_retries = 1
        self._auto_interrupt_tts_enabled = True
        self._auto_interrupt_sample_seconds = 1.0
        self._auto_interrupt_adaptive_enabled = True
        self._auto_interrupt_quiet_rms_threshold = 140.0
        self._auto_interrupt_noisy_rms_threshold = 260.0
        self._auto_interrupt_hits_quiet = 1
        self._auto_interrupt_hits_normal = 2
        self._auto_interrupt_hits_noisy = 3
        self._agent_routing_profile = "rolepack_v1"
        self._chat_prompt_pack_profile = "dynamic_v1"
        self._dictation_target = "active_field"
        self._snap_to_edge_enabled = True
        self._start_hidden = False
        self._launch_at_login_enabled = False
        self._activation_hotkey = "ctrl+alt+v"
        self._text_hotkey = "ctrl+alt+t"


@unittest.skipUnless(SettingsDialog is not None, "PySide6 is not installed")
class SettingsDialogTests(unittest.TestCase):
    def test_settings_dialog_exposes_apply_api(self) -> None:
        self.assertTrue(callable(SettingsDialog.apply))

    def test_settings_dialog_can_be_created_from_widget_state(self) -> None:
        app = QApplication.instance() or QApplication([])
        _ = app

        widget = FakeAvatarWidget()
        dialog = SettingsDialog(widget)

        self.assertIsNotNone(dialog._voice_profile_combo)
        self.assertIsNotNone(dialog._dictation_target_combo)
        self.assertIsNotNone(dialog._auto_interrupt_adaptive_checkbox)
        self.assertIsNotNone(dialog._hotkey_input)


if __name__ == "__main__":
    unittest.main()
