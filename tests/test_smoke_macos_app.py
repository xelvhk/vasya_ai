from __future__ import annotations

import os
import plistlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.smoke_macos_app import (
    MacOSAppSmokeConfig,
    launch_app_executable,
    run_smoke,
    validate_app_bundle,
)


class SmokeMacOSAppTests(unittest.TestCase):
    def test_validate_app_bundle_accepts_expected_pyinstaller_bundle_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppSmokeConfig(root_dir=Path(tmp))
            _create_app_bundle(config)

            checks = validate_app_bundle(config)

        self.assertTrue(all(check.state == "OK" for check in checks))

    def test_validate_app_bundle_reports_missing_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppSmokeConfig(root_dir=Path(tmp))
            _create_app_bundle(config, include_assets=False)

            checks = validate_app_bundle(config)

        failed_names = {check.name for check in checks if check.state == "FAIL"}
        self.assertIn("avatar assets", failed_names)
        self.assertIn("avatar skins", failed_names)

    def test_validate_app_bundle_reports_plist_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppSmokeConfig(root_dir=Path(tmp))
            _create_app_bundle(config, executable_name="Wrong")

            checks = validate_app_bundle(config)

        failures = {check.name: check.message for check in checks if check.state == "FAIL"}
        self.assertIn("CFBundleExecutable", failures)

    def test_run_smoke_skips_launch_when_structure_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppSmokeConfig(root_dir=Path(tmp))

            with patch("scripts.smoke_macos_app.launch_app_executable") as launch:
                with patch("sys.stdout"):
                    exit_code = run_smoke(config, launch=True)

        self.assertEqual(exit_code, 1)
        launch.assert_not_called()

    def test_launch_app_executable_treats_timeout_as_started(self) -> None:
        config = MacOSAppSmokeConfig(root_dir=Path("/repo"))
        process = Mock()
        process.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd="/repo/build/packaging/dist/Vasya AI.app/Contents/MacOS/Vasya AI", timeout=1),
            ("", ""),
        ]

        with patch("scripts.smoke_macos_app.subprocess.Popen", return_value=process):
            check = launch_app_executable(config, timeout_seconds=1, offscreen=False)

        self.assertEqual(check.state, "OK")
        self.assertIn("stayed alive", check.message)
        process.kill.assert_called_once()


def _create_app_bundle(
    config: MacOSAppSmokeConfig,
    *,
    include_assets: bool = True,
    executable_name: str = "Vasya AI",
) -> None:
    config.executable_path.parent.mkdir(parents=True)
    config.resources_path.mkdir(parents=True)
    config.executable_path.write_text("#!/bin/sh\n", encoding="utf-8")
    config.executable_path.chmod(0o755)
    if include_assets:
        (config.resources_path / "assets" / "skins").mkdir(parents=True)

    plist = {
        "CFBundlePackageType": "APPL",
        "CFBundleExecutable": executable_name,
        "CFBundleDisplayName": config.app_name,
    }
    with config.info_plist_path.open("wb") as file:
        plistlib.dump(plist, file)


if __name__ == "__main__":
    unittest.main()
