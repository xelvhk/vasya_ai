from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.package_macos_app import MacOSAppPackageConfig, ditto_zip_command, run_package


class PackageMacOSAppTests(unittest.TestCase):
    def test_ditto_zip_command_keeps_app_bundle_parent(self) -> None:
        config = MacOSAppPackageConfig(root_dir=Path("/repo"))

        command = ditto_zip_command(config)

        self.assertEqual(command[0], "/usr/bin/ditto")
        self.assertIn("--keepParent", command)
        self.assertIn("--sequesterRsrc", command)
        self.assertEqual(command[-2], "/repo/build/packaging/dist/Vasya AI.app")
        self.assertEqual(command[-1], "/repo/build/packaging/release/Vasya-AI-macos-unsigned.zip")

    def test_run_package_rejects_missing_app_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppPackageConfig(root_dir=Path(tmp))

            with patch("sys.stdout"):
                result = run_package(config)

        self.assertEqual(result, 1)

    def test_run_package_dry_run_does_not_create_release_dir_or_call_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSAppPackageConfig(root_dir=Path(tmp))
            config.app_path.mkdir(parents=True)

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

            with patch("scripts.package_macos_app.subprocess.run") as run:
                with patch("sys.stdout"):
                    result = run_package(config)

            self.assertEqual(result, 0)
            self.assertTrue(config.release_path.is_dir())
            run.assert_called_once_with(ditto_zip_command(config), cwd=str(config.root_dir), check=True)


if __name__ == "__main__":
    unittest.main()
