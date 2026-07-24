from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_macos_app import (
    MacOSAppBuildConfig,
    pyinstaller_command,
    pyinstaller_environment,
    resolve_pyinstaller,
    run_build,
)


class BuildMacOSAppTests(unittest.TestCase):
    def test_pyinstaller_command_uses_windowed_onedir_app_with_assets(self) -> None:
        config = MacOSAppBuildConfig(root_dir=Path("/repo"), app_name="Vasya AI")

        command = pyinstaller_command(config, pyinstaller="/repo/.venv/bin/pyinstaller")

        self.assertEqual(command[0], "/repo/.venv/bin/pyinstaller")
        self.assertIn("--windowed", command)
        self.assertIn("--onedir", command)
        self.assertIn("--clean", command)
        self.assertEqual(command[command.index("--name") + 1], "Vasya AI")
        self.assertEqual(command[command.index("--distpath") + 1], "/repo/build/packaging/dist")
        self.assertEqual(command[command.index("--workpath") + 1], "/repo/build/packaging/work")
        self.assertEqual(command[command.index("--specpath") + 1], "/repo/build/packaging/spec")
        self.assertEqual(command[command.index("--add-data") + 1], f"/repo/assets{os.pathsep}assets")
        self.assertEqual(command[-1], "/repo/main.py")

    def test_resolve_pyinstaller_prefers_project_virtualenv_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local_binary = root / ".venv" / "bin" / "pyinstaller"
            local_binary.parent.mkdir(parents=True)
            local_binary.write_text("#!/bin/sh\n", encoding="utf-8")

            self.assertEqual(resolve_pyinstaller(root), str(local_binary))

    def test_run_build_dry_run_does_not_call_subprocess(self) -> None:
        config = MacOSAppBuildConfig(root_dir=Path("/repo"))

        with patch("scripts.build_macos_app.resolve_pyinstaller", return_value=None):
            with patch("scripts.build_macos_app.subprocess.run") as run:
                with patch("sys.stdout"):
                    result = run_build(config, dry_run=True, allow_non_macos=True)

        self.assertEqual(result, 0)
        run.assert_not_called()

    def test_pyinstaller_environment_uses_repo_local_cache_by_default(self) -> None:
        config = MacOSAppBuildConfig(root_dir=Path("/repo"))

        with patch.dict(os.environ, {}, clear=True):
            env = pyinstaller_environment(config)

        self.assertEqual(env["PYINSTALLER_CONFIG_DIR"], "/repo/build/packaging/cache")

    def test_pyinstaller_environment_preserves_explicit_cache_override(self) -> None:
        config = MacOSAppBuildConfig(root_dir=Path("/repo"))

        with patch.dict(os.environ, {"PYINSTALLER_CONFIG_DIR": "/tmp/pyinstaller-cache"}, clear=True):
            env = pyinstaller_environment(config)

        self.assertEqual(env["PYINSTALLER_CONFIG_DIR"], "/tmp/pyinstaller-cache")

    def test_run_build_rejects_non_macos_without_override(self) -> None:
        config = MacOSAppBuildConfig(root_dir=Path("/repo"))

        with patch("scripts.build_macos_app.sys.platform", "linux"):
            with patch("sys.stdout"):
                result = run_build(config, dry_run=True, allow_non_macos=False)

        self.assertEqual(result, 1)
