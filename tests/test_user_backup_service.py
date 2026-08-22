from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import os
import stat
import tempfile
import unittest
from zipfile import ZipFile

from services.user_backup_service import (
    BACKUP_FORMAT,
    BACKUP_VERSION,
    BackupSourceError,
    create_user_backup,
)


class UserBackupServiceTests(unittest.TestCase):
    def test_export_creates_versioned_allowlist_archive_with_integrity_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            project_payload = {
                "version": 1,
                "projects": [
                    {
                        "id": "sample",
                        "name": "Sample",
                        "path": str(root / "sample"),
                        "kind": "python",
                        "priority": 10,
                        "enabled": True,
                    }
                ],
            }
            avatar_payload = {"visible": True, "position": {"x": 10, "y": 20}}
            self._write_json(data_dir / "project_registry.json", project_payload)
            self._write_json(data_dir / "avatar_widget.json", avatar_payload)
            self._write_json(data_dir / "integration_secrets.json", {"token": "do-not-export"})
            self._write_json(data_dir / "integrations.json", {"github_api_token": "legacy-secret"})
            self._write_json(data_dir / "unknown.json", {"private": "payload"})
            (data_dir / "memory_wiki").mkdir()
            (data_dir / "memory_wiki" / "private.md").write_text("private", encoding="utf-8")
            destination = root / "backups" / "vasya.zip"

            result = create_user_backup(
                destination,
                data_dir=data_dir,
                created_at=datetime(2026, 8, 22, 8, 30, tzinfo=timezone.utc),
            )

            self.assertEqual(result.path, destination)
            self.assertEqual(
                result.included_files,
                ("state/avatar_widget.json", "state/project_registry.json"),
            )
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            with ZipFile(destination) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {
                        "manifest.json",
                        "state/avatar_widget.json",
                        "state/project_registry.json",
                    },
                )
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["format"], BACKUP_FORMAT)
                self.assertEqual(manifest["version"], BACKUP_VERSION)
                self.assertEqual(manifest["created_at"], "2026-08-22T08:30:00Z")
                self.assertEqual(manifest["policy"], "portable-json-allowlist-v1")
                self.assertEqual(
                    [item["path"] for item in manifest["files"]],
                    ["state/avatar_widget.json", "state/project_registry.json"],
                )
                for item in manifest["files"]:
                    payload = archive.read(item["path"])
                    self.assertEqual(item["size"], len(payload))
                    self.assertEqual(item["sha256"], hashlib.sha256(payload).hexdigest())

    def test_export_does_not_traverse_symlinked_allowlist_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            outside = root / "outside.json"
            self._write_json(outside, {"visible": True})
            try:
                (data_dir / "avatar_widget.json").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            destination = root / "backup.zip"

            result = create_user_backup(destination, data_dir=data_dir)

            self.assertEqual(result.included_files, ())
            with ZipFile(destination) as archive:
                self.assertEqual(archive.namelist(), ["manifest.json"])

    def test_export_rejects_sensitive_keys_even_in_an_allowlisted_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            self._write_json(
                data_dir / "user_profile.json",
                {"preferences": {"tone": "concise"}, "api_token": "do-not-export"},
            )
            destination = root / "backup.zip"

            with self.assertRaisesRegex(BackupSourceError, "sensitive key"):
                create_user_backup(destination, data_dir=data_dir)

            self.assertFalse(destination.exists())

    def test_export_rejects_camel_case_private_key_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            self._write_json(
                data_dir / "user_profile.json",
                {"preferences": {"privateKeyPem": "do-not-export"}},
            )
            destination = root / "backup.zip"

            with self.assertRaisesRegex(BackupSourceError, "privateKeyPem"):
                create_user_backup(destination, data_dir=data_dir)

            self.assertFalse(destination.exists())

    def test_export_rejects_malformed_json_without_replacing_existing_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            (data_dir / "project_registry.json").write_text("{not-json", encoding="utf-8")
            destination = root / "backup.zip"
            destination.write_bytes(b"previous-backup")

            with self.assertRaisesRegex(BackupSourceError, "valid JSON"):
                create_user_backup(destination, data_dir=data_dir)

            self.assertEqual(destination.read_bytes(), b"previous-backup")

    def test_export_rejects_oversized_allowlist_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            self._write_json(data_dir / "avatar_widget.json", {"value": "x" * 100})

            with self.assertRaisesRegex(BackupSourceError, "size limit"):
                create_user_backup(
                    root / "backup.zip",
                    data_dir=data_dir,
                    max_file_bytes=32,
                )

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
