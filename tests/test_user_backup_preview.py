from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from services.user_backup_service import (
    BackupArchiveError,
    create_user_backup,
    preview_user_backup,
)


class UserBackupPreviewTests(unittest.TestCase):
    def test_preview_classifies_create_unchanged_and_conflict_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "source"
            target_dir = root / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            self._write_json(source_dir / "avatar_widget.json", {"visible": True})
            self._write_json(source_dir / "child_mode.json", {"enabled": False})
            self._write_json(
                source_dir / "project_registry.json",
                {"version": 1, "projects": []},
            )
            (target_dir / "avatar_widget.json").write_bytes(
                (source_dir / "avatar_widget.json").read_bytes()
            )
            self._write_json(
                target_dir / "project_registry.json",
                {"version": 1, "projects": [{"id": "local"}]},
            )
            archive_path = root / "backup.zip"
            create_user_backup(
                archive_path,
                data_dir=source_dir,
                created_at=datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc),
            )
            local_project_before = (target_dir / "project_registry.json").read_bytes()

            preview = preview_user_backup(archive_path, data_dir=target_dir)

            self.assertEqual(preview.created_at, "2026-08-25T09:00:00Z")
            self.assertEqual(
                [(item.path, item.status) for item in preview.items],
                [
                    ("state/avatar_widget.json", "unchanged"),
                    ("state/child_mode.json", "create"),
                    ("state/project_registry.json", "conflict"),
                ],
            )
            self.assertTrue(preview.has_conflicts)
            self.assertFalse((target_dir / "child_mode.json").exists())
            self.assertEqual(
                (target_dir / "project_registry.json").read_bytes(),
                local_project_before,
            )

    def test_preview_does_not_create_missing_target_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = self._create_sample_archive(root)
            target_dir = root / "missing-target"

            preview = preview_user_backup(archive_path, data_dir=target_dir)

            self.assertEqual(
                [(item.path, item.status) for item in preview.items],
                [("state/project_registry.json", "create")],
            )
            self.assertFalse(target_dir.exists())

    def test_preview_rejects_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = self._create_sample_archive(root)
            entries = self._read_entries(archive_path)
            original = entries["state/project_registry.json"]
            tampered = original.replace(b'"projects"', b'"projectx"', 1)
            self.assertEqual(len(tampered), len(original))
            entries["state/project_registry.json"] = tampered
            self._write_entries(archive_path, entries)

            with self.assertRaisesRegex(BackupArchiveError, "checksum"):
                preview_user_backup(archive_path, data_dir=root / "target")

    def test_preview_rejects_unsafe_and_unknown_entries(self) -> None:
        cases = (
            ("../escape.json", "unsafe archive path"),
            ("state/unknown.json", "unexpected archive entry"),
        )
        for entry_name, message in cases:
            with self.subTest(entry_name=entry_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                archive_path = self._create_sample_archive(root)
                with ZipFile(archive_path, mode="a", compression=ZIP_DEFLATED) as archive:
                    archive.writestr(entry_name, b"{}")

                with self.assertRaisesRegex(BackupArchiveError, message):
                    preview_user_backup(archive_path, data_dir=root / "target")

    def test_preview_rejects_duplicate_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = self._create_sample_archive(root)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(archive_path, mode="a", compression=ZIP_DEFLATED) as archive:
                    archive.writestr("state/project_registry.json", b"{}")

            with self.assertRaisesRegex(BackupArchiveError, "duplicate archive entry"):
                preview_user_backup(archive_path, data_dir=root / "target")

    def test_preview_rejects_symlink_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = self._create_sample_archive(root)
            entries = self._read_entries(archive_path)
            self._write_entries(
                archive_path,
                entries,
                symlink_path="state/project_registry.json",
            )

            with self.assertRaisesRegex(BackupArchiveError, "symbolic link"):
                preview_user_backup(archive_path, data_dir=root / "target")

    def test_preview_rejects_future_version_and_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = self._create_sample_archive(root)
            entries = self._read_entries(archive_path)
            manifest = json.loads(entries["manifest.json"])
            manifest["version"] = 99
            entries["manifest.json"] = self._json_bytes(manifest)
            self._write_entries(archive_path, entries)

            with self.assertRaisesRegex(BackupArchiveError, "unsupported backup version"):
                preview_user_backup(archive_path, data_dir=root / "target")

            archive_path = self._create_sample_archive(root)
            entries = self._read_entries(archive_path)
            invalid_payload = b"{not-json"
            manifest = json.loads(entries["manifest.json"])
            manifest["files"][0]["size"] = len(invalid_payload)
            manifest["files"][0]["sha256"] = hashlib.sha256(invalid_payload).hexdigest()
            entries["manifest.json"] = self._json_bytes(manifest)
            entries["state/project_registry.json"] = invalid_payload
            self._write_entries(archive_path, entries)

            with self.assertRaisesRegex(BackupArchiveError, "valid JSON"):
                preview_user_backup(archive_path, data_dir=root / "target")

    def test_preview_rejects_sensitive_payload_with_valid_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = self._create_sample_archive(root)
            entries = self._read_entries(archive_path)
            sensitive_payload = self._json_bytes(
                {"version": 1, "projects": [], "apiToken": "do-not-import"}
            )
            manifest = json.loads(entries["manifest.json"])
            manifest["files"][0]["size"] = len(sensitive_payload)
            manifest["files"][0]["sha256"] = hashlib.sha256(
                sensitive_payload
            ).hexdigest()
            entries["manifest.json"] = self._json_bytes(manifest)
            entries["state/project_registry.json"] = sensitive_payload
            self._write_entries(archive_path, entries)

            with self.assertRaisesRegex(BackupArchiveError, "sensitive key"):
                preview_user_backup(archive_path, data_dir=root / "target")

    def _create_sample_archive(self, root: Path) -> Path:
        source_dir = root / "source"
        source_dir.mkdir(exist_ok=True)
        self._write_json(
            source_dir / "project_registry.json",
            {"version": 1, "projects": []},
        )
        archive_path = root / "backup.zip"
        create_user_backup(archive_path, data_dir=source_dir)
        return archive_path

    @staticmethod
    def _read_entries(path: Path) -> dict[str, bytes]:
        with ZipFile(path) as archive:
            return {info.filename: archive.read(info) for info in archive.infolist()}

    @staticmethod
    def _write_entries(
        path: Path,
        entries: dict[str, bytes],
        *,
        symlink_path: str | None = None,
    ) -> None:
        with ZipFile(path, mode="w", compression=ZIP_DEFLATED) as archive:
            for entry_name, payload in entries.items():
                if entry_name != symlink_path:
                    archive.writestr(entry_name, payload)
                    continue
                info = ZipInfo(entry_name)
                info.create_system = 3
                info.compress_type = ZIP_DEFLATED
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, payload)

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_bytes(UserBackupPreviewTests._json_bytes(payload))

    @staticmethod
    def _json_bytes(payload: object) -> bytes:
        return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


if __name__ == "__main__":
    unittest.main()
