from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.build_macos_doctor import MacOSDoctorBuildConfig, pyinstaller_command, run_build


class BuildMacOSDoctorTests(unittest.TestCase):
    def test_pyinstaller_command_uses_console_onedir_doctor_entrypoint(self) -> None:
        config = MacOSDoctorBuildConfig(root_dir=Path("/repo"), app_name="Vasya AI Doctor")

        command = pyinstaller_command(config, pyinstaller="/repo/.venv/bin/pyinstaller")

        self.assertEqual(command[0], "/repo/.venv/bin/pyinstaller")
        self.assertIn("--console", command)
        self.assertIn("--onedir", command)
        self.assertIn("--clean", command)
        self.assertEqual(command[command.index("--name") + 1], "Vasya AI Doctor")
        self.assertEqual(command[command.index("--distpath") + 1], "/repo/build/packaging/doctor-dist")
        self.assertEqual(command[command.index("--workpath") + 1], "/repo/build/packaging/doctor-work")
        self.assertEqual(command[command.index("--specpath") + 1], "/repo/build/packaging/doctor-spec")
        self.assertEqual(command[command.index("--paths") + 1], "/repo")
        self.assertIn("dateparser", command)
        self.assertIn("googleapiclient", command)
        self.assertIn("google_auth_oauthlib", command)
        self.assertEqual(command[-1], "/repo/scripts/doctor.py")

    def test_run_build_dry_run_does_not_call_subprocess(self) -> None:
        config = MacOSDoctorBuildConfig(root_dir=Path("/repo"))

        with patch("scripts.build_macos_doctor.resolve_pyinstaller", return_value=None):
            with patch("scripts.build_macos_doctor.subprocess.run") as run:
                with patch("sys.stdout"):
                    result = run_build(config, dry_run=True, allow_non_macos=True)

        self.assertEqual(result, 0)
        run.assert_not_called()

    def test_run_build_rejects_non_macos_without_override(self) -> None:
        config = MacOSDoctorBuildConfig(root_dir=Path("/repo"))

        with patch("scripts.build_macos_doctor.sys.platform", "linux"):
            with patch("sys.stdout"):
                result = run_build(config, dry_run=True, allow_non_macos=False)

        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
