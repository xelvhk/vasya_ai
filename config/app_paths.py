from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Mapping


APP_DISPLAY_NAME = "Vasya AI"
APP_SLUG = "vasya-ai"


@dataclass(frozen=True)
class AppPaths:
    root: Path
    config_dir: Path
    data_dir: Path
    logs_dir: Path
    cache_dir: Path
    source_compat: bool = False

    @property
    def env_file(self) -> Path:
        return self.config_dir / ".env"

    @property
    def memory_dir(self) -> Path:
        return self.data_dir / "memory_wiki"

    def config_file(self, name: str) -> Path:
        return self.config_dir / name

    def state_file(self, name: str) -> Path:
        return self.data_dir / name

    def log_file(self, name: str) -> Path:
        return self.logs_dir / name

    def cache_path(self, name: str) -> Path:
        if self.source_compat:
            legacy_names = {
                "tts": "cache",
                "xtts": "xtts_cache",
                "matplotlib": "mpl_cache",
                "benchmarks": "tts_benchmarks",
                "models": "tts_models",
                "engines": "tts_engines",
            }
            return self.data_dir / legacy_names.get(name, name)
        return self.cache_dir / name


@dataclass(frozen=True)
class MigrationResult:
    copied: tuple[str, ...]
    skipped: tuple[str, ...]


def resolve_app_paths(
    *,
    system_name: str | None = None,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
    packaged: bool | None = None,
    source_root: Path | None = None,
) -> AppPaths:
    env = os.environ if environ is None else environ
    runtime_is_packaged = getattr(sys, "frozen", False) if packaged is None else packaged
    project_root = (
        Path(__file__).resolve().parent.parent if source_root is None else Path(source_root)
    )
    override = str(env.get("VASYA_APP_DATA_DIR", "")).strip()
    source_compat = (
        not runtime_is_packaged
        and not override
        and _env_flag(env.get("VASYA_SOURCE_STORAGE_COMPAT", "true"))
    )
    if source_compat:
        storage_dir = project_root / "storage"
        return AppPaths(
            root=project_root,
            config_dir=project_root,
            data_dir=storage_dir,
            logs_dir=storage_dir,
            cache_dir=storage_dir / "cache",
            source_compat=True,
        )

    user_home = Path.home() if home is None else Path(home)
    if override:
        root = _anchored_user_path(override, user_home)
    else:
        root = _platform_data_root(
            system_name=system_name or platform.system(),
            home=user_home,
            environ=env,
        )
    return AppPaths(
        root=root,
        config_dir=root / "config",
        data_dir=root / "data",
        logs_dir=root / "logs",
        cache_dir=root / "cache",
        source_compat=False,
    )


def ensure_app_directories(paths: AppPaths) -> None:
    for directory in (
        paths.config_dir,
        paths.data_dir,
        paths.logs_dir,
        paths.cache_dir,
        paths.memory_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def migrate_legacy_runtime_data(legacy_root: Path, paths: AppPaths) -> MigrationResult:
    legacy_root = Path(legacy_root)
    ensure_app_directories(paths)
    copied: list[str] = []
    skipped: list[str] = []

    _copy_if_missing(legacy_root / ".env", paths.env_file, paths, copied, skipped)
    _copy_if_missing(
        legacy_root / "credentials.json",
        paths.config_file("credentials.json"),
        paths,
        copied,
        skipped,
    )

    storage_dir = legacy_root / "storage"
    for name in _STATE_FILES:
        _copy_if_missing(storage_dir / name, paths.state_file(name), paths, copied, skipped)
    for name in _LOG_FILES:
        _copy_if_missing(storage_dir / name, paths.log_file(name), paths, copied, skipped)

    directory_mappings = (
        ("memory_wiki", paths.memory_dir),
        ("voices", paths.data_dir / "voices"),
        ("cache", paths.cache_path("tts")),
        ("xtts_cache", paths.cache_path("xtts")),
        ("mpl_cache", paths.cache_path("matplotlib")),
        ("matplotlib_cache", paths.cache_path("matplotlib")),
        ("tts_benchmarks", paths.cache_path("benchmarks")),
        ("tts_models", paths.cache_path("models")),
        ("tts_engines", paths.cache_path("engines")),
    )
    for legacy_name, destination in directory_mappings:
        _copy_tree_if_missing(
            storage_dir / legacy_name,
            destination,
            paths,
            copied,
            skipped,
        )

    return MigrationResult(copied=tuple(copied), skipped=tuple(skipped))


def _platform_data_root(
    *,
    system_name: str,
    home: Path,
    environ: Mapping[str, str],
) -> Path:
    normalized_system = system_name.strip().lower()
    if normalized_system == "darwin":
        return home / "Library" / "Application Support" / APP_DISPLAY_NAME
    if normalized_system == "windows":
        appdata = str(environ.get("APPDATA", "")).strip()
        base = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return base / APP_DISPLAY_NAME
    xdg_data_home = str(environ.get("XDG_DATA_HOME", "")).strip()
    base = (
        _anchored_user_path(xdg_data_home, home)
        if xdg_data_home
        else home / ".local" / "share"
    )
    return base / APP_SLUG


def _anchored_user_path(value: str, home: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else home / path


def _copy_tree_if_missing(
    source: Path,
    destination: Path,
    paths: AppPaths,
    copied: list[str],
    skipped: list[str],
) -> None:
    if not source.is_dir() or source.is_symlink():
        return
    for source_file in sorted(source.rglob("*")):
        if not source_file.is_file() or source_file.is_symlink():
            continue
        relative_path = source_file.relative_to(source)
        _copy_if_missing(
            source_file,
            destination / relative_path,
            paths,
            copied,
            skipped,
        )


def _copy_if_missing(
    source: Path,
    destination: Path,
    paths: AppPaths,
    copied: list[str],
    skipped: list[str],
) -> None:
    if not source.is_file() or source.is_symlink():
        return
    label = _destination_label(destination, paths)
    if _same_path(source, destination) or destination.exists():
        skipped.append(label)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if destination.name in _PRIVATE_FILE_NAMES:
        destination.chmod(0o600)
    copied.append(label)


def _destination_label(destination: Path, paths: AppPaths) -> str:
    try:
        return destination.relative_to(paths.root).as_posix()
    except ValueError:
        return str(destination)


def _same_path(left: Path, right: Path) -> bool:
    return left.absolute() == right.absolute()


def _env_flag(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


_STATE_FILES = (
    "avatar_custom_skin.json",
    "avatar_widget.json",
    "calendar.json",
    "child_mode.json",
    "dictation_mode.json",
    "github_notion_sync_state.json",
    "google_token.json",
    "integration_secrets.json",
    "integrations.json",
    "morning_show_state.json",
    "project_registry.json",
    "tasks.json",
    "tts_settings.json",
    "user_profile.json",
    "vasya.db",
)

_PRIVATE_FILE_NAMES = {
    ".env",
    "credentials.json",
    "google_token.json",
    "integration_secrets.json",
    "integrations.json",
}

_LOG_FILES = (
    "interactions.log",
    "launchagent.err.log",
    "launchagent.out.log",
    "voice.log",
)
