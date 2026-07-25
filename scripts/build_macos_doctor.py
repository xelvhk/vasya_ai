from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.build_macos_app import pyinstaller_environment, resolve_pyinstaller  # noqa: E402

DEFAULT_DOCTOR_NAME = "Vasya AI Doctor"


@dataclass(frozen=True)
class MacOSDoctorBuildConfig:
    root_dir: Path
    app_name: str = DEFAULT_DOCTOR_NAME

    @property
    def dist_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "doctor-dist"

    @property
    def work_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "doctor-work"

    @property
    def spec_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "doctor-spec"

    @property
    def cache_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "cache"

    @property
    def entrypoint(self) -> Path:
        return self.root_dir / "scripts" / "doctor.py"


def main() -> None:
    args = _parse_args(sys.argv[1:])
    exit_code = run_build(
        MacOSDoctorBuildConfig(root_dir=ROOT_DIR, app_name=args.name),
        dry_run=args.dry_run,
        allow_non_macos=args.allow_non_macos,
    )
    raise SystemExit(exit_code)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local unsigned macOS doctor companion")
    parser.add_argument("--dry-run", action="store_true", help="Print the PyInstaller command without running it")
    parser.add_argument("--name", default=DEFAULT_DOCTOR_NAME, help="Doctor executable display name")
    parser.add_argument(
        "--allow-non-macos",
        action="store_true",
        help="Allow command generation on non-macOS hosts for CI/tests",
    )
    return parser.parse_args(argv)


def run_build(
    config: MacOSDoctorBuildConfig,
    *,
    dry_run: bool = False,
    allow_non_macos: bool = False,
) -> int:
    if sys.platform != "darwin" and not allow_non_macos:
        print("macOS doctor packaging must run on macOS. Use --dry-run --allow-non-macos to inspect the command.")
        return 1

    pyinstaller = resolve_pyinstaller(config.root_dir)
    if pyinstaller is None:
        if dry_run:
            pyinstaller = "pyinstaller"
        else:
            print("PyInstaller is not installed. Run: .venv/bin/python -m pip install -r requirements-build.txt")
            return 1

    command = pyinstaller_command(config, pyinstaller=pyinstaller)
    if dry_run:
        print(" ".join(command))
        return 0

    subprocess.run(
        command,
        cwd=str(config.root_dir),
        env=pyinstaller_environment(config),
        check=True,
    )
    print(f"Built doctor companion under: {config.dist_path}")
    return 0


def pyinstaller_command(config: MacOSDoctorBuildConfig, *, pyinstaller: str) -> list[str]:
    return [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--console",
        "--onedir",
        "--name",
        config.app_name,
        "--distpath",
        str(config.dist_path),
        "--workpath",
        str(config.work_path),
        "--specpath",
        str(config.spec_path),
        "--paths",
        str(config.root_dir),
        "--hidden-import",
        "dateparser",
        "--hidden-import",
        "googleapiclient",
        "--hidden-import",
        "google_auth_oauthlib",
        str(config.entrypoint),
    ]


if __name__ == "__main__":
    main()
