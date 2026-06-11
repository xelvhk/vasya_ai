from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from scripts import doctor


class DoctorScriptTests(unittest.TestCase):
    def test_report_normalizes_status(self) -> None:
        result = doctor.report("check", "warn", "message")
        self.assertEqual(result.status, "WARN")

    def test_report_rejects_unknown_status(self) -> None:
        with self.assertRaises(ValueError):
            doctor.report("check", "maybe", "message")

    def test_build_summary_for_clean_run(self) -> None:
        results = [
            doctor.report("a", "OK", "ok"),
            doctor.report("b", "OK", "ok"),
        ]
        summary = doctor._build_summary(results)
        self.assertIn("all key checks passed", summary)
        self.assertIn("ok=2", summary)

    def test_build_summary_for_warning_run(self) -> None:
        results = [
            doctor.report("a", "OK", "ok"),
            doctor.report("b", "WARN", "warn"),
        ]
        summary = doctor._build_summary(results)
        self.assertIn("warnings found", summary)
        self.assertIn("warn=1", summary)

    def test_build_summary_for_failed_run(self) -> None:
        results = [
            doctor.report("a", "OK", "ok"),
            doctor.report("b", "FAIL", "fail"),
        ]
        summary = doctor._build_summary(results)
        self.assertIn("issues found", summary)
        self.assertIn("fail=1", summary)

    def test_api_auth_config_fails_without_token_in_protected_mode(self) -> None:
        with patch.object(doctor, "VASYA_API_REQUIRE_AUTH", True), patch.object(
            doctor, "VASYA_API_AUTH_TOKEN", ""
        ):
            result = doctor.check_api_auth_config()
        self.assertEqual(result.status, "FAIL")
        self.assertIn("VASYA_API_AUTH_TOKEN", result.message)

    def test_api_auth_config_warns_when_auth_disabled(self) -> None:
        with patch.object(doctor, "VASYA_API_REQUIRE_AUTH", False):
            result = doctor.check_api_auth_config()
        self.assertEqual(result.status, "WARN")

    def test_python_version_fails_below_minimum(self) -> None:
        with patch.object(doctor.sys, "version_info", (3, 10, 12)):
            result = doctor.check_python_version()
        self.assertEqual(result.status, "FAIL")
        self.assertIn("3.11", result.message)

    def test_tts_backend_is_skipped_in_ci(self) -> None:
        with patch.dict("os.environ", {"CI": "true"}):
            result = doctor.check_tts_backend()
        self.assertEqual(result.status, "OK")
        self.assertIn("CI", result.message)

    def test_tts_backend_warns_for_print_fallback(self) -> None:
        with patch.dict("os.environ", {}, clear=True), patch(
            "voice.backends.get_tts_backend_name",
            return_value="print",
        ), patch(
            "voice.backends.get_tts_backend_status",
            return_value="TTS backend: print",
        ):
            result = doctor.check_tts_backend()
        self.assertEqual(result.status, "WARN")
        self.assertIn("TTS backend", result.message)

    def test_ci_env_does_not_require_local_env_file(self) -> None:
        with patch.dict("os.environ", {"CI": "true"}), patch.object(
            doctor.Path,
            "exists",
            return_value=False,
        ):
            result = doctor.check_env_file()
        self.assertEqual(result.status, "OK")
        self.assertIn("CI", result.message)

    def test_virtualenv_check_returns_result(self) -> None:
        result = doctor.check_virtualenv()
        self.assertIn(result.status, {"OK", "WARN"})
        self.assertEqual(result.name, "virtualenv")

    def test_ci_env_does_not_require_local_ollama_binary(self) -> None:
        with patch.dict("os.environ", {"CI": "true"}), patch.object(
            doctor.shutil,
            "which",
            return_value=None,
        ):
            result = doctor.check_ollama_binary()
        self.assertEqual(result.status, "OK")
        self.assertIn("CI", result.message)

    def test_ollama_binary_check_returns_result(self) -> None:
        with patch.dict("os.environ", {}, clear=True), patch.object(
            doctor.shutil,
            "which",
            return_value=None,
        ):
            result = doctor.check_ollama_binary()
        self.assertEqual(result.status, "FAIL")
        self.assertIn("ollama", result.message)

    def test_ci_env_skips_ollama_server(self) -> None:
        with patch.dict("os.environ", {"CI": "true"}), patch.object(
            doctor.shutil,
            "which",
            return_value="/usr/local/bin/ollama",
        ):
            result = doctor.check_ollama_server()
        self.assertEqual(result.status, "OK")
        self.assertIn("skipped", result.message)

    def test_ci_env_skips_google_calendar(self) -> None:
        with patch.dict("os.environ", {"CI": "true"}):
            result = doctor.check_google_calendar()
        self.assertEqual(result.status, "OK")
        self.assertIn("CI", result.message)

    def test_resolve_exit_code_non_strict_warn(self) -> None:
        results = [doctor.report("a", "WARN", "warn")]
        self.assertEqual(doctor._resolve_exit_code(results, strict=False), 2)

    def test_resolve_exit_code_strict_warn(self) -> None:
        results = [doctor.report("a", "WARN", "warn")]
        self.assertEqual(doctor._resolve_exit_code(results, strict=True), 1)

    def test_run_doctor_quiet_prints_summary_only(self) -> None:
        checks = [doctor.report("a", "OK", "ok")]
        with patch.object(doctor, "run_checks", return_value=checks), patch(
            "sys.stdout",
            new_callable=io.StringIO,
        ) as stdout:
            exit_code = doctor.run_doctor(quiet=True)
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("doctor result:", output)
        self.assertNotIn("== Vasya AI doctor ==", output)

    def test_run_doctor_json_prints_payload(self) -> None:
        checks = [doctor.report("a", "OK", "ok")]
        with patch.object(doctor, "run_checks", return_value=checks), patch(
            "sys.stdout",
            new_callable=io.StringIO,
        ) as stdout:
            exit_code = doctor.run_doctor(json_output=True, strict=True, quiet=True)
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn('"checks"', output)
        self.assertIn('"exit_code": 0', output)

    def test_parse_args_supports_flags(self) -> None:
        args = doctor._parse_args(["--json", "--strict", "--quiet"])
        self.assertTrue(args.json)
        self.assertTrue(args.strict)
        self.assertTrue(args.quiet)


if __name__ == "__main__":
    unittest.main()
