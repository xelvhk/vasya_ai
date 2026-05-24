from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
