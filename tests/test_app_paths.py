from __future__ import annotations

from pathlib import Path
import os
import stat
import tempfile
import unittest

from config.app_paths import (
    ensure_app_directories,
    migrate_legacy_runtime_data,
    resolve_app_paths,
)


class AppPathsTests(unittest.TestCase):
    def test_macos_packaged_paths_use_application_support(self) -> None:
        paths = resolve_app_paths(
            system_name="Darwin",
            home=Path("/Users/alex"),
            environ={},
            packaged=True,
            source_root=Path("/repo"),
        )

        self.assertEqual(paths.root, Path("/Users/alex/Library/Application Support/Vasya AI"))
        self.assertEqual(paths.env_file, paths.root / "config" / ".env")
        self.assertEqual(paths.state_file("vasya.db"), paths.root / "data" / "vasya.db")
        self.assertEqual(paths.log_file("voice.log"), paths.root / "logs" / "voice.log")
        self.assertEqual(paths.cache_path("xtts"), paths.root / "cache" / "xtts")

    def test_windows_packaged_paths_use_appdata(self) -> None:
        paths = resolve_app_paths(
            system_name="Windows",
            home=Path("C:/Users/Alex"),
            environ={"APPDATA": "D:/Profiles/Alex/Roaming"},
            packaged=True,
            source_root=Path("C:/vasya"),
        )

        self.assertEqual(paths.root, Path("D:/Profiles/Alex/Roaming/Vasya AI"))

    def test_linux_packaged_paths_honor_xdg_data_home(self) -> None:
        paths = resolve_app_paths(
            system_name="Linux",
            home=Path("/home/alex"),
            environ={"XDG_DATA_HOME": "/mnt/profile/data"},
            packaged=True,
            source_root=Path("/repo"),
        )

        self.assertEqual(paths.root, Path("/mnt/profile/data/vasya-ai"))

    def test_linux_packaged_paths_fall_back_to_local_share(self) -> None:
        paths = resolve_app_paths(
            system_name="Linux",
            home=Path("/home/alex"),
            environ={},
            packaged=True,
            source_root=Path("/repo"),
        )

        self.assertEqual(paths.root, Path("/home/alex/.local/share/vasya-ai"))

    def test_source_checkout_keeps_repo_storage_without_using_cwd(self) -> None:
        paths = resolve_app_paths(
            system_name="Darwin",
            home=Path("/Users/alex"),
            environ={},
            packaged=False,
            source_root=Path("/repo/vasya"),
        )

        self.assertTrue(paths.source_compat)
        self.assertEqual(paths.env_file, Path("/repo/vasya/.env"))
        self.assertEqual(paths.state_file("vasya.db"), Path("/repo/vasya/storage/vasya.db"))
        self.assertEqual(paths.cache_path("xtts"), Path("/repo/vasya/storage/xtts_cache"))

    def test_explicit_app_data_override_enables_platform_layout(self) -> None:
        paths = resolve_app_paths(
            system_name="Darwin",
            home=Path("/Users/alex"),
            environ={"VASYA_APP_DATA_DIR": "/private/vasya-profile"},
            packaged=False,
            source_root=Path("/repo/vasya"),
        )

        self.assertFalse(paths.source_compat)
        self.assertEqual(paths.root, Path("/private/vasya-profile"))

    def test_relative_app_data_override_is_anchored_to_home(self) -> None:
        paths = resolve_app_paths(
            system_name="Linux",
            home=Path("/home/alex"),
            environ={"VASYA_APP_DATA_DIR": "profiles/vasya"},
            packaged=True,
            source_root=Path("/repo"),
        )

        self.assertEqual(paths.root, Path("/home/alex/profiles/vasya"))

    def test_first_run_creates_only_runtime_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_app_paths(
                system_name="Linux",
                home=Path(tmp),
                environ={"VASYA_APP_DATA_DIR": str(Path(tmp) / "profile")},
                packaged=True,
                source_root=Path("/repo"),
            )

            ensure_app_directories(paths)

            self.assertTrue(paths.config_dir.is_dir())
            self.assertTrue(paths.data_dir.is_dir())
            self.assertTrue(paths.logs_dir.is_dir())
            self.assertTrue(paths.cache_dir.is_dir())
            self.assertFalse(paths.env_file.exists())

    def test_migration_is_idempotent_and_never_overwrites_new_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy_root = root / "legacy"
            (legacy_root / "storage" / "memory_wiki").mkdir(parents=True)
            (legacy_root / ".env").write_text("OLD_ENV=1\n", encoding="utf-8")
            (legacy_root / "storage" / "vasya.db").write_text("old-db", encoding="utf-8")
            (legacy_root / "storage" / "voice.log").write_text("old-log", encoding="utf-8")
            (legacy_root / "storage" / "memory_wiki" / "note.md").write_text(
                "memory", encoding="utf-8"
            )
            paths = resolve_app_paths(
                system_name="Linux",
                home=root,
                environ={"VASYA_APP_DATA_DIR": str(root / "profile")},
                packaged=True,
                source_root=Path("/repo"),
            )
            ensure_app_directories(paths)
            paths.state_file("vasya.db").write_text("new-db", encoding="utf-8")

            first = migrate_legacy_runtime_data(legacy_root, paths)
            second = migrate_legacy_runtime_data(legacy_root, paths)

            self.assertEqual(paths.env_file.read_text(encoding="utf-8"), "OLD_ENV=1\n")
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(paths.env_file.stat().st_mode), 0o600)
            self.assertEqual(paths.state_file("vasya.db").read_text(encoding="utf-8"), "new-db")
            self.assertEqual(paths.log_file("voice.log").read_text(encoding="utf-8"), "old-log")
            self.assertEqual(
                (paths.memory_dir / "note.md").read_text(encoding="utf-8"), "memory"
            )
            self.assertIn("data/vasya.db", first.skipped)
            self.assertEqual(second.copied, ())


if __name__ == "__main__":
    unittest.main()
