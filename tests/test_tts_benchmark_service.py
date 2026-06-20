from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import tts_benchmark_service as bench


class TTSBenchmarkServiceTests(unittest.TestCase):
    def test_xtts_is_skipped_without_heavy_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = bench.build_tts_benchmark_plan(
                backend="xtts",
                text="hello",
                output_dir=Path(tmp),
                include_heavy=False,
            )
        self.assertIsInstance(result, bench.TTSBenchmarkResult)
        assert isinstance(result, bench.TTSBenchmarkResult)
        self.assertEqual(result.status, "SKIP")
        self.assertTrue(result.heavy)
        self.assertIn("--include-heavy", result.failure_reason or "")

    def test_misotts_is_experimental_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = bench.build_tts_benchmark_plan(
                backend="misotts",
                text="hello",
                output_dir=Path(tmp),
            )
        self.assertIsInstance(result, bench.TTSBenchmarkResult)
        assert isinstance(result, bench.TTSBenchmarkResult)
        self.assertEqual(result.status, "SKIP")
        self.assertTrue(result.experimental)
        self.assertIn("experimental", result.failure_reason or "")

    def test_chatterbox_is_skipped_when_package_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "services.tts_benchmark_service.importlib.util.find_spec",
            return_value=None,
        ), patch("services.tts_benchmark_service.CHATTERBOX_PYTHON", ""):
            result = bench.build_tts_benchmark_plan(
                backend="chatterbox",
                text="hello",
                output_dir=Path(tmp),
            )

        self.assertIsInstance(result, bench.TTSBenchmarkResult)
        assert isinstance(result, bench.TTSBenchmarkResult)
        self.assertEqual(result.status, "SKIP")
        self.assertTrue(result.heavy)
        self.assertTrue(result.experimental)
        self.assertIn("pip install chatterbox-tts", result.failure_reason or "")

    def test_chatterbox_plan_uses_isolated_runner_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            python_path = Path(tmp) / "venv_chatterbox" / "bin" / "python"
            python_path.parent.mkdir(parents=True)
            python_path.touch()
            with patch("services.tts_benchmark_service.CHATTERBOX_PYTHON", str(python_path)):
                plan = bench.build_tts_benchmark_plan(
                    backend="chatterbox",
                    text="hello",
                    output_dir=Path(tmp),
                )

        self.assertIsInstance(plan, bench.TTSBenchmarkPlan)
        assert isinstance(plan, bench.TTSBenchmarkPlan)
        self.assertTrue(plan.heavy)
        self.assertTrue(plan.experimental)
        self.assertEqual(plan.command[0], str(python_path))
        self.assertIn("run_chatterbox_tts.py", " ".join(plan.command))
        self.assertIn("--language", plan.command)
        self.assertIn("ru", plan.command)
        self.assertEqual(plan.output_path.name, "chatterbox.wav")

    def test_chatterbox_is_skipped_when_configured_python_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "services.tts_benchmark_service.CHATTERBOX_PYTHON",
            "/missing/chatterbox/python",
        ):
            result = bench.build_tts_benchmark_plan(
                backend="chatterbox",
                text="hello",
                output_dir=Path(tmp),
            )

        self.assertIsInstance(result, bench.TTSBenchmarkResult)
        assert isinstance(result, bench.TTSBenchmarkResult)
        self.assertEqual(result.status, "SKIP")
        self.assertIn("CHATTERBOX_PYTHON", result.failure_reason or "")

    def test_cosyvoice_is_skipped_when_repo_is_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "services.tts_benchmark_service.COSYVOICE_REPO_DIR",
            "",
        ), patch("services.tts_benchmark_service.COSYVOICE_MODEL_DIR", ""):
            result = bench.build_tts_benchmark_plan(
                backend="cosyvoice",
                text="hello",
                output_dir=Path(tmp),
            )

        self.assertIsInstance(result, bench.TTSBenchmarkResult)
        assert isinstance(result, bench.TTSBenchmarkResult)
        self.assertEqual(result.status, "SKIP")
        self.assertTrue(result.heavy)
        self.assertTrue(result.experimental)
        self.assertIn("COSYVOICE_REPO_DIR", result.failure_reason or "")

    def test_cosyvoice_is_skipped_when_model_is_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "CosyVoice"
            repo_dir.mkdir()
            result = None
            with patch("services.tts_benchmark_service.COSYVOICE_REPO_DIR", str(repo_dir)), patch(
                "services.tts_benchmark_service.COSYVOICE_MODEL_DIR",
                "",
            ):
                result = bench.build_tts_benchmark_plan(
                    backend="cosyvoice",
                    text="hello",
                    output_dir=Path(tmp),
                )

        self.assertIsInstance(result, bench.TTSBenchmarkResult)
        assert isinstance(result, bench.TTSBenchmarkResult)
        self.assertEqual(result.status, "SKIP")
        self.assertIn("COSYVOICE_MODEL_DIR", result.failure_reason or "")

    def test_cosyvoice_plan_uses_isolated_runner_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "CosyVoice"
            model_dir = Path(tmp) / "CosyVoice3-0.5B"
            repo_dir.mkdir()
            model_dir.mkdir()
            with patch("services.tts_benchmark_service.COSYVOICE_REPO_DIR", str(repo_dir)), patch(
                "services.tts_benchmark_service.COSYVOICE_MODEL_DIR",
                str(model_dir),
            ), patch("services.tts_benchmark_service.COSYVOICE_SPEAKER", "default"), patch(
                "services.tts_benchmark_service.COSYVOICE_PYTHON",
                "",
            ):
                plan = bench.build_tts_benchmark_plan(
                    backend="cosyvoice",
                    text="hello",
                    output_dir=Path(tmp),
                )

        self.assertIsInstance(plan, bench.TTSBenchmarkPlan)
        assert isinstance(plan, bench.TTSBenchmarkPlan)
        self.assertTrue(plan.heavy)
        self.assertTrue(plan.experimental)
        self.assertEqual(plan.command[0], bench.sys.executable)
        self.assertIn("run_cosyvoice_tts.py", " ".join(plan.command))
        self.assertIn("--repo-dir", plan.command)
        self.assertIn("--model-dir", plan.command)
        self.assertIn("--speaker", plan.command)
        self.assertEqual(plan.output_path.name, "cosyvoice.wav")
        self.assertIsNotNone(plan.env)
        assert plan.env is not None
        self.assertIn("XDG_CACHE_HOME", plan.env)
        self.assertIn("HF_HOME", plan.env)

    def test_cosyvoice3_requires_prompt_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "CosyVoice"
            model_dir = Path(tmp) / "CosyVoice3-0.5B"
            repo_dir.mkdir()
            model_dir.mkdir()
            (model_dir / "cosyvoice3.yaml").touch()
            with patch("services.tts_benchmark_service.COSYVOICE_REPO_DIR", str(repo_dir)), patch(
                "services.tts_benchmark_service.COSYVOICE_MODEL_DIR",
                str(model_dir),
            ), patch("services.tts_benchmark_service.COSYVOICE_PROMPT_WAV", ""), patch(
                "services.tts_benchmark_service.XTTS_SPEAKER_WAV",
                "",
            ):
                result = bench.build_tts_benchmark_plan(
                    backend="cosyvoice",
                    text="hello",
                    output_dir=Path(tmp),
                )

        self.assertIsInstance(result, bench.TTSBenchmarkResult)
        assert isinstance(result, bench.TTSBenchmarkResult)
        self.assertEqual(result.status, "SKIP")
        self.assertIn("COSYVOICE_PROMPT_WAV", result.failure_reason or "")

    def test_cosyvoice3_plan_passes_prompt_wav_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "CosyVoice"
            model_dir = Path(tmp) / "CosyVoice3-0.5B"
            prompt_wav = Path(tmp) / "prompt.wav"
            repo_dir.mkdir()
            model_dir.mkdir()
            (model_dir / "cosyvoice3.yaml").touch()
            prompt_wav.write_bytes(b"wav")
            with patch("services.tts_benchmark_service.COSYVOICE_REPO_DIR", str(repo_dir)), patch(
                "services.tts_benchmark_service.COSYVOICE_MODEL_DIR",
                str(model_dir),
            ), patch("services.tts_benchmark_service.COSYVOICE_PROMPT_WAV", str(prompt_wav)), patch(
                "services.tts_benchmark_service.COSYVOICE_PROMPT_TEXT",
                "sample prompt",
            ), patch("services.tts_benchmark_service.COSYVOICE_PYTHON", ""):
                plan = bench.build_tts_benchmark_plan(
                    backend="cosyvoice",
                    text="hello",
                    output_dir=Path(tmp),
                )

        self.assertIsInstance(plan, bench.TTSBenchmarkPlan)
        assert isinstance(plan, bench.TTSBenchmarkPlan)
        self.assertIn("--prompt-wav", plan.command)
        self.assertIn(str(prompt_wav), plan.command)
        self.assertIn("--prompt-text", plan.command)
        self.assertIn("sample prompt", plan.command)

    def test_cosyvoice_is_skipped_when_configured_python_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "CosyVoice"
            model_dir = Path(tmp) / "CosyVoice3-0.5B"
            repo_dir.mkdir()
            model_dir.mkdir()
            with patch("services.tts_benchmark_service.COSYVOICE_REPO_DIR", str(repo_dir)), patch(
                "services.tts_benchmark_service.COSYVOICE_MODEL_DIR",
                str(model_dir),
            ), patch("services.tts_benchmark_service.COSYVOICE_PYTHON", "/missing/cosyvoice/python"):
                result = bench.build_tts_benchmark_plan(
                    backend="cosyvoice",
                    text="hello",
                    output_dir=Path(tmp),
                )

        self.assertIsInstance(result, bench.TTSBenchmarkResult)
        assert isinstance(result, bench.TTSBenchmarkResult)
        self.assertEqual(result.status, "SKIP")
        self.assertIn("COSYVOICE_PYTHON", result.failure_reason or "")

    def test_include_experimental_adds_quality_candidates_and_misotts(self) -> None:
        with patch(
            "services.tts_benchmark_service.build_tts_benchmark_plan",
            side_effect=lambda backend, text, output_dir, include_heavy=False: bench._skip(
                backend=backend,
                selected_backend=backend,
                reason="test",
            ),
        ):
            snapshot = bench.run_tts_benchmark(
                text="hello",
                backends=["say"],
                include_experimental=True,
            )

        results = snapshot["results"]
        self.assertIsInstance(results, list)
        self.assertEqual([item["backend"] for item in results], ["say", "chatterbox", "cosyvoice", "misotts"])

    def test_say_plan_uses_file_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "services.tts_benchmark_service.get_platform_name",
            return_value="macos",
        ), patch("services.tts_benchmark_service.shutil.which", return_value="/usr/bin/say"):
            plan = bench.build_tts_benchmark_plan(
                backend="say",
                text="hello",
                output_dir=Path(tmp),
            )
        self.assertIsInstance(plan, bench.TTSBenchmarkPlan)
        assert isinstance(plan, bench.TTSBenchmarkPlan)
        self.assertIn("-o", plan.command)
        self.assertEqual(plan.output_path.suffix, ".aiff")

    def test_header_only_audio_file_is_not_counted_as_started(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header_only = Path(tmp) / "say.aiff"
            header_only.write_bytes(b"\0" * 4096)

            self.assertFalse(bench._audio_file_started(header_only))

    def test_xtts_plan_uses_project_local_runner_and_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            xtts_bin = Path(tmp) / "venv_xtts" / "bin"
            xtts_bin.mkdir(parents=True)
            tts_command = xtts_bin / "tts"
            python_command = xtts_bin / "python"
            tts_command.touch()
            python_command.touch()
            with patch(
                "services.tts_benchmark_service._resolve_command",
                return_value=str(tts_command),
            ), patch(
                "services.tts_benchmark_service.get_profile_speaker_wav",
                return_value=Path("/tmp/speaker.wav"),
            ), patch("services.tts_benchmark_service.XTTS_TRUST_LOCAL_CHECKPOINT", True):
                plan = bench.build_tts_benchmark_plan(
                    backend="xtts",
                    text="hello",
                    output_dir=Path(tmp),
                    include_heavy=True,
                )

        self.assertIsInstance(plan, bench.TTSBenchmarkPlan)
        assert isinstance(plan, bench.TTSBenchmarkPlan)
        self.assertIn("run_xtts_tts.py", " ".join(plan.command))
        self.assertEqual(plan.command[0], str(python_command))
        self.assertIn("--trust-local-checkpoint", plan.command)
        self.assertIsNotNone(plan.env)
        assert plan.env is not None
        self.assertIn("TTS_HOME", plan.env)
        self.assertIn("MPLCONFIGDIR", plan.env)
        self.assertIn("XDG_CACHE_HOME", plan.env)
        self.assertIn("HF_HOME", plan.env)

    def test_xtts_plan_can_disable_trusted_checkpoint_opt_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "services.tts_benchmark_service._resolve_command",
            return_value="/tmp/venv_xtts/bin/tts",
        ), patch(
            "services.tts_benchmark_service.get_profile_speaker_wav",
            return_value=Path("/tmp/speaker.wav"),
        ), patch("services.tts_benchmark_service.XTTS_TRUST_LOCAL_CHECKPOINT", False):
            plan = bench.build_tts_benchmark_plan(
                backend="xtts",
                text="hello",
                output_dir=Path(tmp),
                include_heavy=True,
            )

        self.assertIsInstance(plan, bench.TTSBenchmarkPlan)
        assert isinstance(plan, bench.TTSBenchmarkPlan)
        self.assertNotIn("--trust-local-checkpoint", plan.command)

    def test_run_benchmark_uses_injected_runner(self) -> None:
        def fake_runner(plan: bench.TTSBenchmarkPlan) -> bench.ProcessTiming:
            plan.output_path.write_bytes(b"audio")
            return bench.ProcessTiming(time_to_first_audio_ms=12.34, total_synthesis_ms=56.78)

        with tempfile.TemporaryDirectory() as tmp, patch(
            "services.tts_benchmark_service.get_platform_name",
            return_value="macos",
        ), patch("services.tts_benchmark_service.shutil.which", return_value="/usr/bin/say"):
            snapshot = bench.run_tts_benchmark(
                text="hello",
                backends=["say"],
                artifact_dir=Path(tmp),
                process_runner=fake_runner,
            )

        results = snapshot["results"]
        self.assertIsInstance(results, list)
        self.assertEqual(results[0]["status"], "OK")
        self.assertEqual(results[0]["time_to_first_audio_ms"], 12.34)
        self.assertEqual(results[0]["total_synthesis_ms"], 56.78)

    def test_copy_plan_for_hybrid_rewrites_output_path_in_command(self) -> None:
        original = bench.TTSBenchmarkPlan(
            backend="piper",
            selected_backend="piper",
            command=["piper", "--output_file", "/tmp/piper.wav"],
            output_path=Path("/tmp/piper.wav"),
            env={"TTS_HOME": "/tmp/tts-cache"},
        )

        copied = bench._copy_plan_for_backend(original, backend="hybrid", status_suffix="test")

        self.assertEqual(copied.output_path, Path("/tmp/hybrid-piper.wav"))
        self.assertIn("/tmp/hybrid-piper.wav", copied.command)
        self.assertNotIn("/tmp/piper.wav", copied.command)
        self.assertEqual(copied.env, {"TTS_HOME": "/tmp/tts-cache"})

    def test_text_report_includes_skip_reason(self) -> None:
        snapshot = {
            "text": "hello",
            "include_heavy": False,
            "include_experimental": False,
            "save_artifacts": False,
            "results": [
                {
                    "backend": "xtts",
                    "selected_backend": "xtts",
                    "status": "SKIP",
                    "failure_reason": "rerun with --include-heavy",
                }
            ],
        }
        report = bench.build_tts_benchmark_report(snapshot)
        self.assertIn("xtts", report)
        self.assertIn("--include-heavy", report)


if __name__ == "__main__":
    unittest.main()
