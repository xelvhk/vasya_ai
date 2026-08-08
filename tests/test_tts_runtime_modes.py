from __future__ import annotations

import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from voice import backends


class TTSRuntimeModeTests(unittest.TestCase):
    def tearDown(self) -> None:
        backends.reset_tts_backend()

    def test_auto_quality_mode_selects_cosyvoice_when_available(self) -> None:
        with patch.object(backends, "TTS_BACKEND", "auto"), patch.object(
            backends,
            "TTS_RUNTIME_MODE",
            "quality",
        ), patch.object(backends, "is_cosyvoice_available", return_value=True):
            backend = backends.get_tts_backend()

        self.assertIsInstance(backend, backends.CosyVoiceTTSBackend)

    def test_auto_mode_selects_cosyvoice_for_quality_profile_when_available(self) -> None:
        quality_profile = backends.get_voice_profile("vasya_quality_cosyvoice")
        with patch.object(backends, "TTS_BACKEND", "auto"), patch.object(
            backends,
            "TTS_RUNTIME_MODE",
            "fast",
        ), patch.object(backends, "get_active_voice_profile", return_value=quality_profile), patch.object(
            backends,
            "is_cosyvoice_available",
            return_value=True,
        ):
            backend = backends.get_tts_backend()

        self.assertIsInstance(backend, backends.CosyVoiceTTSBackend)

    def test_auto_quality_mode_falls_back_to_piper_when_cosyvoice_is_unavailable(self) -> None:
        piper_profile = backends.get_voice_profile("ruslan_direct")
        with patch.object(backends, "TTS_BACKEND", "auto"), patch.object(
            backends,
            "TTS_RUNTIME_MODE",
            "quality",
        ), patch.object(backends, "is_cosyvoice_available", return_value=False), patch.object(
            backends,
            "is_piper_available",
            return_value=True,
        ), patch.object(
            backends,
            "get_active_voice_profile",
            return_value=piper_profile,
        ):
            backend = backends.get_tts_backend()

        self.assertIsInstance(backend, backends.PiperTTSBackend)

    def test_auto_mode_does_not_use_say_as_implicit_fallback(self) -> None:
        with patch.object(backends, "TTS_BACKEND", "auto"), patch.object(
            backends,
            "TTS_RUNTIME_MODE",
            "fast",
        ), patch.object(backends, "is_cosyvoice_available", return_value=False), patch.object(
            backends,
            "is_piper_available",
            return_value=False,
        ), patch.object(backends, "is_xtts_available", return_value=False), patch.object(
            backends,
            "is_xtts_command_available",
            return_value=False,
        ), patch.object(backends, "get_platform_name", return_value="macos"):
            backend = backends.get_tts_backend()

        self.assertIsInstance(backend, backends.PrintTTSBackend)

    def test_cosyvoice_backend_builds_runner_command_with_local_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_dir = root / "CosyVoice"
            model_dir = root / "CosyVoice3-0.5B"
            prompt_wav = root / "prompt.wav"
            python_path = root / "venv_cosyvoice" / "bin" / "python"
            output_path = root / "out.wav"
            repo_dir.mkdir()
            model_dir.mkdir()
            (model_dir / "cosyvoice3.yaml").touch()
            prompt_wav.write_bytes(b"wav")
            python_path.parent.mkdir(parents=True)
            python_path.touch()

            with patch.object(backends, "COSYVOICE_REPO_DIR", str(repo_dir)), patch.object(
                backends,
                "COSYVOICE_MODEL_DIR",
                str(model_dir),
            ), patch.object(backends, "COSYVOICE_PROMPT_WAV", str(prompt_wav)), patch.object(
                backends,
                "COSYVOICE_PYTHON",
                str(python_path),
            ), patch.object(backends, "COSYVOICE_PROMPT_TEXT", "sample prompt"), patch.object(
                backends,
                "TTS_CACHE_DIR",
                str(root / "cache"),
            ):
                command, env = backends.CosyVoiceTTSBackend()._build_command(
                    text="hello",
                    output_path=output_path,
                )

        self.assertEqual(command[0], str(python_path))
        self.assertIn("run_cosyvoice_tts.py", " ".join(command))
        self.assertIn("--prompt-wav", command)
        self.assertIn(str(prompt_wav), command)
        self.assertIn("--prompt-text", command)
        self.assertIn("sample prompt", command)
        self.assertIn("XDG_CACHE_HOME", env)
        self.assertIn("HF_HOME", env)
        self.assertIn("MPLCONFIGDIR", env)

    def test_cosyvoice_availability_requires_prompt_for_cosyvoice3(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_dir = root / "CosyVoice"
            model_dir = root / "CosyVoice3-0.5B"
            python_path = root / "venv_cosyvoice" / "bin" / "python"
            repo_dir.mkdir()
            model_dir.mkdir()
            (model_dir / "cosyvoice3.yaml").touch()
            python_path.parent.mkdir(parents=True)
            python_path.touch()

            with patch.object(backends, "COSYVOICE_REPO_DIR", str(repo_dir)), patch.object(
                backends,
                "COSYVOICE_MODEL_DIR",
                str(model_dir),
            ), patch.object(backends, "COSYVOICE_PROMPT_WAV", ""), patch.object(
                backends,
                "XTTS_SPEAKER_WAV",
                "",
            ), patch.object(backends, "COSYVOICE_PYTHON", str(python_path)):
                self.assertFalse(backends.is_cosyvoice_available())

    def test_quality_mode_status_does_not_report_unrelated_active_profile(self) -> None:
        with patch.object(backends, "TTS_BACKEND", "auto"), patch.object(
            backends,
            "TTS_RUNTIME_MODE",
            "quality",
        ), patch.object(backends, "is_cosyvoice_available", return_value=True), patch.object(
            backends,
            "COSYVOICE_MODEL_DIR",
            "/tmp/CosyVoice3-0.5B",
        ):
            status = backends.get_tts_backend_status()

        self.assertIn("cosyvoice quality mode", status)
        self.assertNotIn("Алекса", status)

    def test_cosyvoice_speak_cleans_temp_file_when_configuration_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "cosyvoice-temp.wav"
            output_path.write_bytes(b"partial")

            class TempFileContext:
                def __enter__(self) -> SimpleNamespace:
                    return SimpleNamespace(name=str(output_path))

                def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
                    return None

            with patch.object(backends.tempfile, "NamedTemporaryFile", return_value=TempFileContext()), patch.object(
                backends,
                "COSYVOICE_REPO_DIR",
                "",
            ):
                with self.assertRaises(RuntimeError):
                    backends.CosyVoiceTTSBackend().speak("hello")

            self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
