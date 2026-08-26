from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Any, Literal
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo


BACKUP_FORMAT = "vasya-user-backup"
BACKUP_VERSION = 1
BACKUP_POLICY = "portable-json-allowlist-v1"
DEFAULT_MAX_FILE_BYTES = 8 * 1024 * 1024


class BackupSourceError(ValueError):
    """Raised when user state cannot be exported without risking data exposure."""


class BackupArchiveError(ValueError):
    """Raised when an import archive cannot be previewed safely."""


class BackupRestoreError(ValueError):
    """Raised when a validated backup cannot be applied safely."""


class BackupConflictError(BackupRestoreError):
    """Raised when restore requires explicit conflict confirmation."""

    def __init__(self, conflicts: tuple[str, ...]) -> None:
        self.conflicts = conflicts
        super().__init__(f"backup restore has conflicts: {', '.join(conflicts)}")


@dataclass(frozen=True)
class UserBackupResult:
    path: Path
    included_files: tuple[str, ...]


@dataclass(frozen=True)
class BackupPreviewItem:
    path: str
    status: Literal["create", "unchanged", "conflict"]
    size: int
    sha256: str
    detail: str


@dataclass(frozen=True)
class UserBackupPreview:
    archive_path: Path
    created_at: str
    items: tuple[BackupPreviewItem, ...]

    @property
    def has_conflicts(self) -> bool:
        return any(item.status == "conflict" for item in self.items)


@dataclass(frozen=True)
class UserBackupRestoreResult:
    archive_path: Path
    created: tuple[str, ...]
    replaced: tuple[str, ...]
    unchanged: tuple[str, ...]


@dataclass(frozen=True)
class _ManifestEntry:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class _BackupEntry:
    archive_path: str
    payload: bytes


@dataclass(frozen=True)
class _ValidatedEntry:
    manifest: _ManifestEntry
    payload: bytes


@dataclass(frozen=True)
class _ValidatedBackup:
    archive_path: Path
    created_at: str
    entries: tuple[_ValidatedEntry, ...]


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

DEFAULT_MAX_ARCHIVE_BYTES = DEFAULT_MAX_FILE_BYTES * len(PORTABLE_STATE_FILES) + 1024 * 1024
DEFAULT_MAX_MANIFEST_BYTES = 256 * 1024
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


def preview_user_backup(
    archive_path: str | Path,
    *,
    data_dir: str | Path,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
) -> UserBackupPreview:
    """Validate a user backup and classify changes without writing local state."""

    backup = _load_validated_backup(
        archive_path,
        max_file_bytes=max_file_bytes,
        max_archive_bytes=max_archive_bytes,
    )
    target_dir = Path(data_dir).expanduser()
    return UserBackupPreview(
        archive_path=backup.archive_path,
        created_at=backup.created_at,
        items=tuple(
            _preview_entry(entry.manifest, payload=entry.payload, data_dir=target_dir)
            for entry in backup.entries
        ),
    )


def restore_user_backup(
    archive_path: str | Path,
    *,
    data_dir: str | Path,
    allow_conflicts: bool = False,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
) -> UserBackupRestoreResult:
    """Validate and restore portable state, requiring opt-in conflict replacement."""

    if not isinstance(allow_conflicts, bool):
        raise ValueError("allow_conflicts must be a boolean")
    backup = _load_validated_backup(
        archive_path,
        max_file_bytes=max_file_bytes,
        max_archive_bytes=max_archive_bytes,
    )
    target_dir = Path(data_dir).expanduser()
    preview_items = tuple(
        _preview_entry(entry.manifest, payload=entry.payload, data_dir=target_dir)
        for entry in backup.entries
    )
    conflicts = tuple(item.path for item in preview_items if item.status == "conflict")
    unsafe_conflicts = tuple(
        item.path
        for item in preview_items
        if item.status == "conflict" and item.detail != "archive and local state differ"
    )
    if unsafe_conflicts or (conflicts and not allow_conflicts):
        raise BackupConflictError(conflicts)

    created = tuple(item.path for item in preview_items if item.status == "create")
    replaced = tuple(item.path for item in preview_items if item.status == "conflict")
    unchanged = tuple(item.path for item in preview_items if item.status == "unchanged")
    if created or replaced:
        _apply_validated_backup(
            backup.entries,
            preview_items=preview_items,
            data_dir=target_dir,
        )
    return UserBackupRestoreResult(
        archive_path=backup.archive_path,
        created=created,
        replaced=replaced,
        unchanged=unchanged,
    )


def _load_validated_backup(
    archive_path: str | Path,
    *,
    max_file_bytes: int,
    max_archive_bytes: int,
) -> _ValidatedBackup:
    _validate_positive_limit(max_file_bytes, field="max_file_bytes")
    _validate_positive_limit(max_archive_bytes, field="max_archive_bytes")
    source_path = Path(archive_path).expanduser()
    if source_path.is_symlink() or not source_path.is_file():
        raise BackupArchiveError("backup archive must be a regular file")
    try:
        if source_path.stat().st_size > max_archive_bytes:
            raise BackupArchiveError("backup archive exceeds the size limit")
    except OSError as exc:
        raise BackupArchiveError("backup archive could not be inspected") from exc

    try:
        with ZipFile(source_path) as archive:
            infos = archive.infolist()
            info_by_path = _validate_archive_members(
                infos,
                max_file_bytes=max_file_bytes,
                max_archive_bytes=max_archive_bytes,
            )
            manifest_info = info_by_path.get("manifest.json")
            if manifest_info is None:
                raise BackupArchiveError("backup manifest is missing")
            if manifest_info.file_size > DEFAULT_MAX_MANIFEST_BYTES:
                raise BackupArchiveError("backup manifest exceeds the size limit")
            manifest_payload = _read_archive_entry(archive, manifest_info)
            created_at, manifest_entries = _parse_manifest(
                manifest_payload,
                max_file_bytes=max_file_bytes,
            )
            declared_paths = {entry.path for entry in manifest_entries}
            archived_paths = set(info_by_path) - {"manifest.json"}
            if declared_paths != archived_paths:
                raise BackupArchiveError("backup entries do not match the manifest")

            validated_entries: list[_ValidatedEntry] = []
            for entry in manifest_entries:
                payload = _read_archive_entry(archive, info_by_path[entry.path])
                if len(payload) != entry.size:
                    raise BackupArchiveError(f"backup entry size does not match: {entry.path}")
                if hashlib.sha256(payload).hexdigest() != entry.sha256:
                    raise BackupArchiveError(
                        f"backup entry checksum does not match: {entry.path}"
                    )
                try:
                    parsed = _parse_json(payload, file_name=entry.path)
                except BackupSourceError as exc:
                    raise BackupArchiveError(
                        f"backup entry is not valid JSON: {entry.path}"
                    ) from exc
                sensitive_key = _find_sensitive_key(parsed)
                if sensitive_key is not None:
                    raise BackupArchiveError(
                        f"backup entry contains a sensitive key: {entry.path}:{sensitive_key}"
                    )
                validated_entries.append(_ValidatedEntry(manifest=entry, payload=payload))
    except BackupArchiveError:
        raise
    except (BadZipFile, OSError, RuntimeError) as exc:
        raise BackupArchiveError("backup archive could not be read safely") from exc

    return _ValidatedBackup(
        archive_path=source_path,
        created_at=created_at,
        entries=tuple(validated_entries),
    )


def _apply_validated_backup(
    entries: tuple[_ValidatedEntry, ...],
    *,
    preview_items: tuple[BackupPreviewItem, ...],
    data_dir: Path,
) -> None:
    if data_dir.is_symlink() or (data_dir.exists() and not data_dir.is_dir()):
        raise BackupRestoreError("backup target must be a regular directory")

    data_dir_existed = data_dir.exists()
    try:
        data_dir.parent.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(mode=0o700, exist_ok=True)
    except OSError as exc:
        raise BackupRestoreError("backup target directory could not be created") from exc

    entry_by_path = {entry.manifest.path: entry for entry in entries}
    changed_items = tuple(item for item in preview_items if item.status != "unchanged")
    try:
        with tempfile.TemporaryDirectory(
            dir=data_dir.parent,
            prefix=".vasya-restore.",
        ) as temporary_name:
            temporary_dir = Path(temporary_name)
            staged_dir = temporary_dir / "staged"
            rollback_dir = temporary_dir / "rollback"
            staged_dir.mkdir(mode=0o700)
            rollback_dir.mkdir(mode=0o700)

            for item in changed_items:
                staged_path = staged_dir / PurePosixPath(item.path).name
                staged_path.write_bytes(entry_by_path[item.path].payload)
                os.chmod(staged_path, 0o600)

            current_items = tuple(
                _preview_entry(
                    entry_by_path[item.path].manifest,
                    payload=entry_by_path[item.path].payload,
                    data_dir=data_dir,
                )
                for item in preview_items
            )
            if current_items != preview_items:
                raise BackupRestoreError("local state changed during backup restore")

            applied_targets: list[Path] = []
            moved_originals: list[tuple[Path, Path]] = []
            try:
                for item in changed_items:
                    file_name = PurePosixPath(item.path).name
                    target_path = data_dir / file_name
                    staged_path = staged_dir / file_name
                    if item.status == "conflict":
                        rollback_path = rollback_dir / file_name
                        os.replace(target_path, rollback_path)
                        moved_originals.append((rollback_path, target_path))
                    elif target_path.is_symlink() or target_path.exists():
                        raise OSError(f"restore target appeared unexpectedly: {file_name}")
                    os.replace(staged_path, target_path)
                    applied_targets.append(target_path)
                    os.chmod(target_path, 0o600)
            except OSError as exc:
                rollback_errors: list[OSError] = []
                for target_path in reversed(applied_targets):
                    try:
                        if target_path.is_symlink() or target_path.exists():
                            target_path.unlink()
                    except OSError as rollback_exc:
                        rollback_errors.append(rollback_exc)
                for rollback_path, target_path in reversed(moved_originals):
                    try:
                        os.replace(rollback_path, target_path)
                    except OSError as rollback_exc:
                        rollback_errors.append(rollback_exc)
                message = "backup restore failed and rollback was incomplete"
                if not rollback_errors:
                    message = "backup restore failed; local state was rolled back"
                raise BackupRestoreError(message) from exc
    except BackupRestoreError:
        raise
    except OSError as exc:
        raise BackupRestoreError("backup restore staging failed") from exc
    finally:
        if not data_dir_existed:
            try:
                if data_dir.exists() and not any(data_dir.iterdir()):
                    data_dir.rmdir()
            except OSError:
                pass


def _validate_positive_limit(value: int, *, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")


def _validate_archive_members(
    infos: list[ZipInfo],
    *,
    max_file_bytes: int,
    max_archive_bytes: int,
) -> dict[str, ZipInfo]:
    allowed_paths = {f"state/{name}" for name in PORTABLE_STATE_FILES}
    info_by_path: dict[str, ZipInfo] = {}
    total_size = 0
    for info in infos:
        path = info.filename
        if not _is_safe_archive_path(path):
            raise BackupArchiveError(f"unsafe archive path: {path}")
        if path in info_by_path:
            raise BackupArchiveError(f"duplicate archive entry: {path}")
        if _is_zip_symlink(info):
            raise BackupArchiveError(f"backup entry is a symbolic link: {path}")
        if info.is_dir() or path not in {"manifest.json", *allowed_paths}:
            raise BackupArchiveError(f"unexpected archive entry: {path}")
        if info.flag_bits & 0x1:
            raise BackupArchiveError(f"encrypted backup entry is not supported: {path}")
        entry_limit = DEFAULT_MAX_MANIFEST_BYTES if path == "manifest.json" else max_file_bytes
        if info.file_size < 0 or info.file_size > entry_limit:
            raise BackupArchiveError(f"backup entry exceeds the size limit: {path}")
        total_size += info.file_size
        if total_size > max_archive_bytes:
            raise BackupArchiveError("backup archive expands beyond the size limit")
        info_by_path[path] = info
    return info_by_path


def _is_safe_archive_path(path: str) -> bool:
    if not path or "\\" in path or "\x00" in path or path.startswith("/"):
        return False
    parts = path.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


def _is_zip_symlink(info: ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _read_archive_entry(archive: ZipFile, info: ZipInfo) -> bytes:
    try:
        return archive.read(info)
    except (BadZipFile, OSError, RuntimeError) as exc:
        raise BackupArchiveError(f"backup entry could not be read: {info.filename}") from exc


def _parse_manifest(
    payload: bytes,
    *,
    max_file_bytes: int,
) -> tuple[str, tuple[_ManifestEntry, ...]]:
    try:
        manifest = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupArchiveError("backup manifest is not valid JSON") from exc
    if not isinstance(manifest, dict):
        raise BackupArchiveError("backup manifest root must be an object")
    if manifest.get("format") != BACKUP_FORMAT:
        raise BackupArchiveError("unsupported backup format")
    version = manifest.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != BACKUP_VERSION:
        raise BackupArchiveError("unsupported backup version")
    if manifest.get("policy") != BACKUP_POLICY:
        raise BackupArchiveError("unsupported backup policy")
    created_at = manifest.get("created_at")
    if not isinstance(created_at, str) or not _is_timezone_timestamp(created_at):
        raise BackupArchiveError("backup manifest timestamp is invalid")
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        raise BackupArchiveError("backup manifest files must be a list")

    allowed_paths = {f"state/{name}" for name in PORTABLE_STATE_FILES}
    entries: list[_ManifestEntry] = []
    seen_paths: set[str] = set()
    for raw_entry in raw_files:
        if not isinstance(raw_entry, dict):
            raise BackupArchiveError("backup manifest entry must be an object")
        path = raw_entry.get("path")
        size = raw_entry.get("size")
        checksum = raw_entry.get("sha256")
        if not isinstance(path, str) or not _is_safe_archive_path(path):
            raise BackupArchiveError("backup manifest contains an unsafe path")
        if path not in allowed_paths:
            raise BackupArchiveError(f"backup manifest entry is not allowed: {path}")
        if path in seen_paths:
            raise BackupArchiveError(f"duplicate backup manifest entry: {path}")
        if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= max_file_bytes:
            raise BackupArchiveError(f"backup manifest size is invalid: {path}")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise BackupArchiveError(f"backup manifest checksum is invalid: {path}")
        seen_paths.add(path)
        entries.append(_ManifestEntry(path=path, size=size, sha256=checksum))
    return created_at, tuple(entries)


def _is_timezone_timestamp(value: str) -> bool:
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _preview_entry(
    entry: _ManifestEntry,
    *,
    payload: bytes,
    data_dir: Path,
) -> BackupPreviewItem:
    local_path = data_dir / PurePosixPath(entry.path).name
    if local_path.is_symlink():
        status: Literal["create", "unchanged", "conflict"] = "conflict"
        detail = "local path is a symbolic link"
    elif not local_path.exists():
        status = "create"
        detail = "local state file does not exist"
    elif not local_path.is_file():
        status = "conflict"
        detail = "local path is not a regular file"
    else:
        try:
            local_payload = local_path.read_bytes()
        except OSError:
            status = "conflict"
            detail = "local state file could not be read"
        else:
            if local_payload == payload:
                status = "unchanged"
                detail = "archive and local state match"
            else:
                status = "conflict"
                detail = "archive and local state differ"
    return BackupPreviewItem(
        path=entry.path,
        status=status,
        size=entry.size,
        sha256=entry.sha256,
        detail=detail,
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
