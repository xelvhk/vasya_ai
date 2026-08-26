from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from services.user_backup_service import (
    BackupArchiveError,
    BackupConflictError,
    BackupRestoreError,
    create_user_backup,
    preview_user_backup,
    restore_user_backup,
)


class UserBackupRestoreTests(unittest.TestCase):
    def test_restore_round_trip_creates_portable_state_without_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            expected = {
                "avatar_widget.json": {"visible": True, "position": {"x": 10, "y": 20}},
                "project_registry.json": {"version": 1, "projects": []},
                "user_profile.json": {"preferences": {"tone": "concise"}},
            }
            for file_name, payload in expected.items():
                self._write_json(source_dir / file_name, payload)
            archive_path = root / "backup.zip"
            create_user_backup(
                archive_path,
                data_dir=source_dir,
                created_at=datetime(2026, 8, 26, 9, 0, tzinfo=timezone.utc),
            )

            result = restore_user_backup(archive_path, data_dir=target_dir)

            self.assertEqual(
                result.created,
                (
                    "state/avatar_widget.json",
                    "state/project_registry.json",
                    "state/user_profile.json",
                ),
            )
            self.assertEqual(result.replaced, ())
            self.assertEqual(result.unchanged, ())
            for file_name in expected:
                self.assertEqual(
                    (target_dir / file_name).read_bytes(),
                    (source_dir / file_name).read_bytes(),
                )
                if os.name != "nt":
                    self.assertEqual(
                        stat.S_IMODE((target_dir / file_name).stat().st_mode),
                        0o600,
                    )
            preview = preview_user_backup(archive_path, data_dir=target_dir)
            self.assertEqual(
                [item.status for item in preview.items],
                ["unchanged", "unchanged", "unchanged"],
            )

    def test_restore_refuses_conflicts_before_creating_or_replacing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            self._write_json(source_dir / "child_mode.json", {"enabled": True})
            self._write_json(source_dir / "project_registry.json", {"version": 1, "projects": []})
            local_payload = self._json_bytes({"version": 1, "projects": [{"id": "keep-local"}]})
            (target_dir / "project_registry.json").write_bytes(local_payload)
            archive_path = root / "backup.zip"
            create_user_backup(archive_path, data_dir=source_dir)

            with self.assertRaises(BackupConflictError) as raised:
                restore_user_backup(archive_path, data_dir=target_dir)

            self.assertEqual(raised.exception.conflicts, ("state/project_registry.json",))
            self.assertFalse((target_dir / "child_mode.json").exists())
            self.assertEqual((target_dir / "project_registry.json").read_bytes(), local_payload)

    def test_restore_replaces_regular_conflict_only_with_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            self._write_json(source_dir / "avatar_widget.json", {"visible": True})
            self._write_json(source_dir / "child_mode.json", {"enabled": True})
            self._write_json(source_dir / "project_registry.json", {"version": 1, "projects": []})
            (target_dir / "avatar_widget.json").write_bytes((source_dir / "avatar_widget.json").read_bytes())
            self._write_json(target_dir / "project_registry.json", {"version": 1})
            archive_path = root / "backup.zip"
            create_user_backup(archive_path, data_dir=source_dir)

            result = restore_user_backup(archive_path, data_dir=target_dir, allow_conflicts=True)

            self.assertEqual(result.created, ("state/child_mode.json",))
            self.assertEqual(result.replaced, ("state/project_registry.json",))
            self.assertEqual(result.unchanged, ("state/avatar_widget.json",))
            self.assertEqual(
                (target_dir / "project_registry.json").read_bytes(),
                (source_dir / "project_registry.json").read_bytes(),
            )

    def test_restore_never_replaces_a_symlink_even_with_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            self._write_json(source_dir / "project_registry.json", {"version": 1})
            outside = root / "outside.json"
            outside_payload = self._json_bytes({"outside": "keep"})
            outside.write_bytes(outside_payload)
            try:
                (target_dir / "project_registry.json").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            archive_path = root / "backup.zip"
            create_user_backup(archive_path, data_dir=source_dir)

            with self.assertRaises(BackupConflictError):
                restore_user_backup(archive_path, data_dir=target_dir, allow_conflicts=True)

            self.assertTrue((target_dir / "project_registry.json").is_symlink())
            self.assertEqual(outside.read_bytes(), outside_payload)

    def test_restore_rolls_back_every_file_when_apply_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            for file_name in ("avatar_widget.json", "project_registry.json"):
                self._write_json(source_dir / file_name, {"source": file_name})
                self._write_json(target_dir / file_name, {"local": file_name})
            originals = {path.name: path.read_bytes() for path in target_dir.iterdir()}
            archive_path = root / "backup.zip"
            create_user_backup(archive_path, data_dir=source_dir)
            real_replace = os.replace
            failed = False

            def fail_second_staged_replace(source: object, destination: object) -> None:
                nonlocal failed
                source_path = Path(source)
                destination_path = Path(destination)
                if not failed and source_path.parent.name == "staged" and destination_path.name == "project_registry.json":
                    failed = True
                    raise OSError("injected restore failure")
                real_replace(source, destination)

            with patch("services.user_backup_service.os.replace", side_effect=fail_second_staged_replace):
                with self.assertRaises(BackupRestoreError):
                    restore_user_backup(archive_path, data_dir=target_dir, allow_conflicts=True)

            self.assertTrue(failed)
            self.assertEqual(
                {path.name: path.read_bytes() for path in target_dir.iterdir()},
                originals,
            )

    def test_restore_revalidates_archive_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "not-a-backup.zip"
            archive_path.write_bytes(b"not a ZIP")
            target_dir = root / "target"

            with self.assertRaises(BackupArchiveError):
                restore_user_backup(archive_path, data_dir=target_dir)

            self.assertFalse(target_dir.exists())

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_bytes(UserBackupRestoreTests._json_bytes(payload))

    @staticmethod
    def _json_bytes(payload: object) -> bytes:
        return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


if __name__ == "__main__":
    unittest.main()
