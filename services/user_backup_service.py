from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


BACKUP_FORMAT = "vasya-user-backup"
BACKUP_VERSION = 1
BACKUP_POLICY = "portable-json-allowlist-v1"
DEFAULT_MAX_FILE_BYTES = 8 * 1024 * 1024


class BackupSourceError(ValueError):
    """Raised when user state cannot be exported without risking data exposure."""


@dataclass(frozen=True)
class UserBackupResult:
    path: Path
    included_files: tuple[str, ...]


@dataclass(frozen=True)
class _BackupEntry:
    archive_path: str
    payload: bytes


PORTABLE_STATE_FILES = (
    "avatar_custom_skin.json",
    "avatar_widget.json",
    "child_mode.json",
    "dictation_mode.json",
    "morning_show_state.json",
    "project_registry.json",
    "tts_settings.json",
    "user_profile.json",
)

_SENSITIVE_KEY_PARTS = {
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}
_SENSITIVE_KEY_NAMES = {
    "access_key",
    "api_key",
    "private_key",
}


def create_user_backup(
    destination: str | Path,
    *,
    data_dir: str | Path,
    created_at: datetime | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> UserBackupResult:
    """Export portable non-secret JSON state to an atomic versioned ZIP archive."""

    if (
        isinstance(max_file_bytes, bool)
        or not isinstance(max_file_bytes, int)
        or max_file_bytes <= 0
    ):
        raise ValueError("max_file_bytes must be a positive integer")
    destination_path = Path(destination).expanduser()
    source_dir = Path(data_dir).expanduser()
    entries = _collect_entries(source_dir, max_file_bytes=max_file_bytes)
    manifest = _build_manifest(entries, created_at=created_at)
    _write_archive(destination_path, manifest=manifest, entries=entries)
    return UserBackupResult(
        path=destination_path,
        included_files=tuple(entry.archive_path for entry in entries),
    )


def _collect_entries(data_dir: Path, *, max_file_bytes: int) -> tuple[_BackupEntry, ...]:
    entries: list[_BackupEntry] = []
    for file_name in PORTABLE_STATE_FILES:
        source_path = data_dir / file_name
        if source_path.is_symlink() or not source_path.is_file():
            continue
        try:
            file_size = source_path.stat().st_size
        except OSError as exc:
            raise BackupSourceError(f"backup source could not be inspected: {file_name}") from exc
        if file_size > max_file_bytes:
            raise BackupSourceError(f"backup source exceeds the size limit: {file_name}")
        try:
            payload = source_path.read_bytes()
        except OSError as exc:
            raise BackupSourceError(f"backup source could not be read: {file_name}") from exc
        if len(payload) > max_file_bytes:
            raise BackupSourceError(f"backup source exceeds the size limit: {file_name}")
        parsed = _parse_json(payload, file_name=file_name)
        sensitive_key = _find_sensitive_key(parsed)
        if sensitive_key is not None:
            raise BackupSourceError(
                f"backup source contains a sensitive key: {file_name}:{sensitive_key}"
            )
        entries.append(
            _BackupEntry(
                archive_path=f"state/{file_name}",
                payload=payload,
            )
        )
    return tuple(entries)


def _parse_json(payload: bytes, *, file_name: str) -> Any:
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupSourceError(f"backup source is not valid JSON: {file_name}") from exc


def _find_sensitive_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                return key
            nested_match = _find_sensitive_key(nested_value)
            if nested_match is not None:
                return nested_match
    elif isinstance(value, list):
        for item in value:
            nested_match = _find_sensitive_key(item)
            if nested_match is not None:
                return nested_match
    return None


def _is_sensitive_key(key: str) -> bool:
    snake_case = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    normalized = re.sub(r"[^a-z0-9]+", "_", snake_case.lower()).strip("_")
    if any(
        normalized == name or normalized.startswith(f"{name}_")
        for name in _SENSITIVE_KEY_NAMES
    ):
        return True
    return any(part in _SENSITIVE_KEY_PARTS for part in normalized.split("_"))


def _build_manifest(
    entries: tuple[_BackupEntry, ...],
    *,
    created_at: datetime | None,
) -> bytes:
    timestamp = datetime.now(timezone.utc) if created_at is None else created_at
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("created_at must include a timezone")
    timestamp_text = timestamp.astimezone(timezone.utc).isoformat(timespec="seconds")
    if timestamp_text.endswith("+00:00"):
        timestamp_text = f"{timestamp_text[:-6]}Z"
    payload = {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "created_at": timestamp_text,
        "policy": BACKUP_POLICY,
        "files": [
            {
                "path": entry.archive_path,
                "size": len(entry.payload),
                "sha256": hashlib.sha256(entry.payload).hexdigest(),
            }
            for entry in entries
        ],
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_archive(
    destination: Path,
    *,
    manifest: bytes,
    entries: tuple[_BackupEntry, ...],
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
        with ZipFile(temporary_path, mode="w", compression=ZIP_DEFLATED) as archive:
            _write_zip_entry(archive, "manifest.json", manifest)
            for entry in entries:
                _write_zip_entry(archive, entry.archive_path, entry.payload)
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _write_zip_entry(archive: ZipFile, path: str, payload: bytes) -> None:
    info = ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    archive.writestr(info, payload)
