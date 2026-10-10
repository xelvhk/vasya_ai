from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication

from scripts.ui.focus_radio import FocusRadio


class FocusRadioPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QCoreApplication.instance() or QCoreApplication([])

    def test_no_autoplay_and_assistant_audio_policy(self) -> None:
        radio = FocusRadio(self.application, mode="rain", volume=0.4)
        self.assertEqual(radio.snapshot()["playing"], False)
        self.assertEqual(radio._player.source().isEmpty(), True)
        radio.set_assistant_state("speaking")
        self.assertAlmostEqual(radio._audio.volume(), 0.072)
        radio.set_assistant_state("listening")
        self.assertEqual(radio.snapshot()["interrupted"], True)
        radio.set_assistant_state("idle")
        self.assertAlmostEqual(radio._audio.volume(), 0.4)
        radio.set_volume(2)
        self.assertEqual(radio.snapshot()["volume"], 1)

    def test_mode_selected_while_paused_loads_the_requested_track(self) -> None:
        radio = FocusRadio(self.application, mode="warm")
        radio.set_mode("night")
        radio.play()
        self.assertTrue(radio._player.source().toLocalFile().endswith("focus-night.mp3"))
        radio.pause()
        radio.set_mode("pulse")
        radio.play()
        self.assertTrue(radio._player.source().toLocalFile().endswith("focus-pulse.mp3"))
        radio.pause()
