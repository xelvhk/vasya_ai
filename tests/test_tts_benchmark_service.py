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
        )

        copied = bench._copy_plan_for_backend(original, backend="hybrid", status_suffix="test")

        self.assertEqual(copied.output_path, Path("/tmp/hybrid-piper.wav"))
        self.assertIn("/tmp/hybrid-piper.wav", copied.command)
        self.assertNotIn("/tmp/piper.wav", copied.command)

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
