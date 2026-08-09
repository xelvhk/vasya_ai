from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from config import settings
from config.app_paths import AppPaths


class SettingsEnvTests(unittest.TestCase):
    def test_dotenv_path_uses_repo_env_in_source_runtime(self) -> None:
        with patch.object(settings.sys, "frozen", False, create=True):
            self.assertEqual(
                settings._dotenv_path_for_runtime(),
                settings._BASE_DIR / ".env",
            )

    def test_dotenv_path_uses_app_data_in_packaged_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "profile"
            with patch.object(settings.sys, "frozen", True, create=True), patch.dict(
                settings.os.environ,
                {"VASYA_APP_DATA_DIR": str(profile)},
                clear=False,
            ):
                env_path = settings._dotenv_path_for_runtime()

            self.assertEqual(env_path, profile / "config" / ".env")
            self.assertTrue(env_path.exists())
            self.assertTrue((profile / "data").is_dir())
            self.assertTrue((profile / "logs").is_dir())
            self.assertTrue((profile / "cache").is_dir())

    def test_runtime_path_keeps_absolute_override(self) -> None:
        with patch.dict(settings.os.environ, {"TEST_STATE_FILE": "/tmp/custom.json"}):
            value = settings._runtime_path(
                "TEST_STATE_FILE",
                settings.APP_PATHS.state_file("default.json"),
                legacy_default="storage/default.json",
            )

        self.assertEqual(value, "/tmp/custom.json")

    def test_runtime_path_resolves_source_relative_to_repo(self) -> None:
        with patch.dict(settings.os.environ, {"TEST_STATE_FILE": "storage/custom.json"}):
            value = settings._runtime_path(
                "TEST_STATE_FILE",
                settings.APP_PATHS.state_file("default.json"),
            )

        self.assertEqual(value, str(settings._BASE_DIR / "storage" / "custom.json"))

    def test_runtime_path_translates_legacy_default_in_platform_mode(self) -> None:
        root = Path("/profile")
        paths = AppPaths(
            root=root,
            config_dir=root / "config",
            data_dir=root / "data",
            logs_dir=root / "logs",
            cache_dir=root / "cache",
        )
        with patch.object(settings, "APP_PATHS", paths), patch.dict(
            settings.os.environ, {"TEST_STATE_FILE": "storage/default.json"}
        ):
            value = settings._runtime_path(
                "TEST_STATE_FILE",
                paths.state_file("default.json"),
                legacy_default="storage/default.json",
            )

        self.assertEqual(value, "/profile/data/default.json")


if __name__ == "__main__":
    unittest.main()
