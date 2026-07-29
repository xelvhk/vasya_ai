from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.smoke_macos_unpacked_zip import (
    MacOSUnpackedZipSmokeConfig,
    launch_unpacked_app_with_open,
    run_unpacked_doctor,
    unpack_zip_artifact,
    validate_first_run_env,
    validate_unpacked_payload,
)


class SmokeMacOSUnpackedZipTests(unittest.TestCase):
    def test_validate_unpacked_payload_accepts_expected_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_unpacked_payload(root)

            checks = validate_unpacked_payload(root)

        self.assertTrue(all(check.state == "OK" for check in checks))

    def test_validate_unpacked_payload_rejects_payload_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_unpacked_payload(root)
            (root / "payload").mkdir()

            checks = validate_unpacked_payload(root)

        failures = {check.name for check in checks if check.state == "FAIL"}
        self.assertIn("staging wrapper", failures)

    def test_run_unpacked_doctor_accepts_diagnostic_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_unpacked_payload(root)
            result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="doctor result: issues found (ok=8, warn=3, fail=1, total=12)\n",
                stderr="",
            )

            with patch("scripts.smoke_macos_unpacked_zip.subprocess.run", return_value=result):
                check = run_unpacked_doctor(root, timeout_seconds=1)

        self.assertEqual(check.state, "OK")
        self.assertIn("doctor result", check.message)

    def test_run_unpacked_doctor_rejects_crash_without_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_unpacked_payload(root)
            result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Traceback")

            with patch("scripts.smoke_macos_unpacked_zip.subprocess.run", return_value=result):
                check = run_unpacked_doctor(root, timeout_seconds=1)

        self.assertEqual(check.state, "FAIL")

    def test_validate_first_run_env_accepts_generated_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("VASYA_API_AUTH_TOKEN=generated-token\n", encoding="utf-8")

            check = validate_first_run_env(root)

        self.assertEqual(check.state, "OK")

    def test_validate_first_run_env_rejects_empty_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("VASYA_API_AUTH_TOKEN=\n", encoding="utf-8")

            check = validate_first_run_env(root)

        self.assertEqual(check.state, "FAIL")
        self.assertIn("empty", check.message)

    def test_unpack_zip_artifact_uses_ditto_extract(self) -> None:
        config = MacOSUnpackedZipSmokeConfig(root_dir=Path("/repo"))
        run = Mock()

        with tempfile.TemporaryDirectory() as tmp:
            checks = None
            with patch("scripts.smoke_macos_unpacked_zip.subprocess.run", run):
                checks = unpack_zip_artifact(config, Path(tmp))

        self.assertEqual(checks[0].state, "OK")
        run.assert_called_once_with(
            [
                "/usr/bin/ditto",
                "-x",
                "-k",
                "/repo/build/packaging/release/Vasya-AI-macos-unsigned.zip",
                tmp,
            ],
            cwd="/repo",
            check=True,
        )

    def test_launch_unpacked_app_with_open_treats_timeout_as_started(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_unpacked_payload(root)
            process = Mock()
            process.communicate.side_effect = [
                subprocess.TimeoutExpired(cmd="/usr/bin/open", timeout=1),
                ("", ""),
            ]

            with patch("scripts.smoke_macos_unpacked_zip.platform.system", return_value="Darwin"):
                with patch("scripts.smoke_macos_unpacked_zip.subprocess.Popen", return_value=process) as popen:
                    with patch("scripts.smoke_macos_unpacked_zip._request_app_quit") as quit_app:
                        check = launch_unpacked_app_with_open(root, timeout_seconds=1)

        self.assertEqual(check.state, "OK")
        self.assertIn("stayed alive", check.message)
        popen.assert_called_once_with(
            ["/usr/bin/open", "-W", str(root / "Vasya AI.app")],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        quit_app.assert_called_once()
        process.terminate.assert_called_once()

    def test_launch_unpacked_app_with_open_rejects_non_macos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.smoke_macos_unpacked_zip.platform.system", return_value="Linux"):
                check = launch_unpacked_app_with_open(Path(tmp), timeout_seconds=1)

        self.assertEqual(check.state, "FAIL")
        self.assertIn("requires macOS", check.message)


def _create_unpacked_payload(root: Path) -> None:
    app_executable = root / "Vasya AI.app" / "Contents" / "MacOS" / "Vasya AI"
    info_plist = root / "Vasya AI.app" / "Contents" / "Info.plist"
    doctor_executable = root / "Vasya AI Doctor" / "Vasya AI Doctor"
    app_executable.parent.mkdir(parents=True)
    doctor_executable.parent.mkdir(parents=True)
    app_executable.write_text("#!/bin/sh\n", encoding="utf-8")
    info_plist.write_text("plist", encoding="utf-8")
    doctor_executable.write_text("#!/bin/sh\n", encoding="utf-8")
    doctor_executable.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
