from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_APP_NAME = "Vasya AI"


@dataclass(frozen=True)
class MacOSAppBuildConfig:
    root_dir: Path
    app_name: str = DEFAULT_APP_NAME

    @property
    def dist_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "dist"

    @property
    def work_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "work"

    @property
    def spec_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "spec"

    @property
    def assets_path(self) -> Path:
        return self.root_dir / "assets"

    @property
    def entrypoint(self) -> Path:
        return self.root_dir / "main.py"


def main() -> None:
    args = _parse_args(sys.argv[1:])
    exit_code = run_build(
        MacOSAppBuildConfig(root_dir=ROOT_DIR, app_name=args.name),
        dry_run=args.dry_run,
        allow_non_macos=args.allow_non_macos,
    )
    raise SystemExit(exit_code)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local unsigned macOS .app prototype")
    parser.add_argument("--dry-run", action="store_true", help="Print the PyInstaller command without running it")
    parser.add_argument("--name", default=DEFAULT_APP_NAME, help="macOS app bundle display name")
    parser.add_argument(
        "--allow-non-macos",
        action="store_true",
        help="Allow command generation on non-macOS hosts for CI/tests",
    )
    return parser.parse_args(argv)


def run_build(
    config: MacOSAppBuildConfig,
    *,
    dry_run: bool = False,
    allow_non_macos: bool = False,
) -> int:
    if sys.platform != "darwin" and not allow_non_macos:
        print("macOS packaging must run on macOS. Use --dry-run --allow-non-macos to inspect the command.")
        return 1

    pyinstaller = resolve_pyinstaller(config.root_dir)
    if pyinstaller is None:
        if dry_run:
            pyinstaller = "pyinstaller"
        else:
            print("PyInstaller is not installed. Run: .venv/bin/pip install pyinstaller")
            return 1

    command = pyinstaller_command(config, pyinstaller=pyinstaller)
    if dry_run:
        print(" ".join(command))
        return 0

    subprocess.run(command, cwd=str(config.root_dir), check=True)
    print(f"Built app prototype under: {config.dist_path}")
    return 0


def resolve_pyinstaller(root_dir: Path) -> str | None:
    local_binary = root_dir / ".venv" / "bin" / "pyinstaller"
    if local_binary.exists():
        return str(local_binary)
    return shutil.which("pyinstaller")


def pyinstaller_command(config: MacOSAppBuildConfig, *, pyinstaller: str) -> list[str]:
    return [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name",
        config.app_name,
        "--distpath",
        str(config.dist_path),
        "--workpath",
        str(config.work_path),
        "--specpath",
        str(config.spec_path),
        "--add-data",
        f"{config.assets_path}{os.pathsep}assets",
        str(config.entrypoint),
    ]


if __name__ == "__main__":
    main()
