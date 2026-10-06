from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from voice import backends


class PiperCommandRecoveryTests(unittest.TestCase):
    def test_stale_configured_path_uses_installed_python_module(self) -> None:
        with patch("voice.backends._resolve_command", return_value=None), patch(
            "voice.backends.importlib.util.find_spec", return_value=object()
        ):
            command = backends._resolve_piper_command()
        self.assertEqual(command, [backends.sys.executable, "-m", "piper"])

    def test_broken_venv_script_shebang_uses_python_module(self) -> None:
        with TemporaryDirectory() as tmp:
            script = Path(tmp) / "piper"
            script.write_text("#!/missing/old-venv/python\n", encoding="utf-8")
            with patch("voice.backends._resolve_command", return_value=str(script)), patch(
                "voice.backends.importlib.util.find_spec", return_value=object()
            ):
                command = backends._resolve_piper_command()
        self.assertEqual(command, [backends.sys.executable, "-m", "piper"])

    def test_missing_command_and_module_returns_unavailable(self) -> None:
        with patch("voice.backends._resolve_command", return_value=None), patch(
            "voice.backends.importlib.util.find_spec", side_effect=ModuleNotFoundError
        ):
            command = backends._resolve_piper_command()
        self.assertIsNone(command)


if __name__ == "__main__":
    unittest.main()
