from __future__ import annotations

import unittest
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from voice import backends


class SileroTTSSelectionTests(unittest.TestCase):
    def tearDown(self) -> None:
        backends._TTS_BACKEND = None

    def test_auto_selects_silero_when_default_profile_is_ready(self) -> None:
        with (
            patch.object(backends, "TTS_BACKEND", "auto"),
            patch.object(backends, "get_active_voice_profile", return_value=backends.get_voice_profile("silero_aidar")),
            patch.object(backends, "is_silero_available", return_value=True),
        ):
            backend = backends.get_tts_backend()
        self.assertEqual(backend.name, "silero")

    def test_auto_falls_back_to_piper_when_silero_is_unavailable(self) -> None:
        with (
            patch.object(backends, "TTS_BACKEND", "auto"),
            patch.object(backends, "get_active_voice_profile", return_value=backends.get_voice_profile("silero_aidar")),
            patch.object(backends, "is_silero_available", return_value=False),
            patch.object(backends, "is_piper_available", return_value=True),
        ):
            backend = backends.get_tts_backend()
        self.assertEqual(backend.name, "piper")

    def test_aidar_profile_is_available_to_settings(self) -> None:
        from voice.profiles import get_voice_profile

        profile = get_voice_profile("silero_aidar")
        self.assertEqual(profile.backend, "silero")
        self.assertEqual(profile.gender, "мужской")

    def test_silero_applies_exact_tempo_and_reuses_worker(self) -> None:
        backend = backends.SileroTTSBackend()
        worker = SimpleNamespace(stdin=StringIO(), stdout=StringIO('{"ok": true}\n{"ok": true}\n'))
        with (
            patch.object(backends, "is_silero_available", return_value=True),
            patch.object(backend, "_get_worker", return_value=worker) as get_worker,
            patch.object(backend, "_play_audio_file") as play,
            patch.object(backends.subprocess, "run") as run,
        ):
            backend.speak("Первый ответ")
            backend.speak("Второй ответ")
        self.assertEqual(get_worker.call_count, 2)
        self.assertEqual(play.call_count, 2)
        self.assertEqual(run.call_count, 2)
        self.assertIn("atempo=1.25", run.call_args.args[0])
        self.assertIn("Первый ответ", worker.stdin.getvalue())
        self.assertIn("Второй ответ", worker.stdin.getvalue())


if __name__ == "__main__":
    unittest.main()
