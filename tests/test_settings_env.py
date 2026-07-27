from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from config import settings


class SettingsEnvTests(unittest.TestCase):
    def test_dotenv_path_uses_default_search_in_source_runtime(self) -> None:
        with patch.object(settings.sys, "frozen", False, create=True):
            self.assertIsNone(settings._dotenv_path_for_runtime())

    def test_dotenv_path_uses_working_directory_in_packaged_runtime(self) -> None:
        with patch.object(settings.sys, "frozen", True, create=True):
            with patch.object(settings.Path, "cwd", return_value=Path("/tmp/Vasya AI")):
                self.assertEqual(settings._dotenv_path_for_runtime(), Path("/tmp/Vasya AI/.env"))


if __name__ == "__main__":
    unittest.main()
