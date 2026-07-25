from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch

from scripts.package_macos_app import (
    MacOSAppPackageConfig,
    ditto_payload_commands,
    ditto_zip_command,
    run_package,
)


class PackageMacOSAppTests(unittest.TestCase):
    def test_ditto_payload_commands_stage_app_and_doctor_payloads(self) -> None:
        config = MacOSAppPackageConfig(root_dir=Path("/repo"))

        commands = ditto_payload_commands(config)

        self.assertEqual(
            commands,
            [
                [
                    "/usr/bin/ditto",
                    "/repo/build/packaging/dist/Vasya AI.app",
                    "/repo/build/packaging/release/payload/Vasya AI.app",
                ],
                [
                    "/usr/bin/ditto",
                    "/repo/build/packaging/doctor-dist/Vasya AI Doctor",
                    "/repo/build/packaging/release/payload/Vasya AI Doctor",
                ],
            ],
        )

    def test_ditto_zip_command_archives_staged_payload_contents(self) -> None:
        config = MacOSAppPackageConfig(root_dir=Path("/repo"))

        command = ditto_zip_command(config)

        self.assertEqual(command[0], "/usr/bin/ditto")
        self.assertIn("--sequesterRsrc", command)
        self.assertNotIn("--keepParent", command)
        self.assertEqual(command[-2], "/repo/build/packaging/release/payload")
        self.assertEqual(command[-1], "/repo/build/packaging/release/Vasya-AI-macos-unsigned.zip")

    def test_run_package_rejects_missing_app_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppPackageConfig(root_dir=Path(tmp))

            with patch("sys.stdout"):
                result = run_package(config)

        self.assertEqual(result, 1)

    def test_run_package_rejects_missing_doctor_companion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppPackageConfig(root_dir=Path(tmp))
            config.app_path.mkdir(parents=True)

            with patch("sys.stdout"):
                result = run_package(config)

        self.assertEqual(result, 1)

    def test_run_package_dry_run_does_not_create_release_dir_or_call_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppPackageConfig(root_dir=Path(tmp))
            config.app_path.mkdir(parents=True)
            config.doctor_path.mkdir(parents=True)

            with patch("scripts.package_macos_app.subprocess.run") as run:
                with patch("sys.stdout"):
                    result = run_package(config, dry_run=True)

        self.assertEqual(result, 0)
        self.assertFalse(config.release_path.exists())
        run.assert_not_called()

    def test_run_package_creates_release_dir_and_runs_ditto(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppPackageConfig(root_dir=Path(tmp))
            config.app_path.mkdir(parents=True)
            config.doctor_path.mkdir(parents=True)

            with patch("scripts.package_macos_app.subprocess.run") as run:
                with patch("sys.stdout"):
                    result = run_package(config)

            self.assertEqual(result, 0)
            self.assertTrue(config.release_path.is_dir())
            self.assertTrue(config.payload_path.is_dir())
            run.assert_has_calls(
                [
                    call(command, cwd=str(config.root_dir), check=True)
                    for command in ditto_payload_commands(config) + [ditto_zip_command(config)]
                ]
            )


if __name__ == "__main__":
    unittest.main()
