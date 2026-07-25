from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_APP_NAME = "Vasya AI"
DEFAULT_ARTIFACT_NAME = "Vasya-AI-macos-unsigned.zip"


@dataclass(frozen=True)
class MacOSAppPackageConfig:
    root_dir: Path
    app_name: str = DEFAULT_APP_NAME
    artifact_name: str = DEFAULT_ARTIFACT_NAME

    @property
    def app_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "dist" / f"{self.app_name}.app"

    @property
    def doctor_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "doctor-dist" / "Vasya AI Doctor"

    @property
    def release_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "release"

    @property
    def payload_path(self) -> Path:
        return self.release_path / "payload"

    @property
    def artifact_path(self) -> Path:
        return self.release_path / self.artifact_name


def main() -> None:
    args = _parse_args(sys.argv[1:])
    exit_code = run_package(
        MacOSAppPackageConfig(root_dir=ROOT_DIR, app_name=args.name, artifact_name=args.artifact_name),
        dry_run=args.dry_run,
    )
    raise SystemExit(exit_code)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package the local unsigned macOS .app prototype")
    parser.add_argument("--dry-run", action="store_true", help="Print the archive command without running it")
    parser.add_argument("--name", default=DEFAULT_APP_NAME, help="macOS app bundle display name")
    parser.add_argument("--artifact-name", default=DEFAULT_ARTIFACT_NAME, help="Output archive filename")
    return parser.parse_args(argv)


def run_package(config: MacOSAppPackageConfig, *, dry_run: bool = False) -> int:
    if not config.app_path.is_dir():
        print(f"Missing app bundle: {config.app_path}. Run scripts/build_macos_app.py first.")
        return 1
    if not config.doctor_path.is_dir():
        print(f"Missing doctor companion: {config.doctor_path}. Run scripts/build_macos_doctor.py first.")
        return 1

    command = ditto_zip_command(config)
    if dry_run:
        for item in ditto_payload_commands(config) + [command]:
            print(" ".join(item))
        return 0

    config.release_path.mkdir(parents=True, exist_ok=True)
    if config.payload_path.exists():
        shutil.rmtree(config.payload_path)
    config.payload_path.mkdir(parents=True)
    for item in ditto_payload_commands(config):
        subprocess.run(item, cwd=str(config.root_dir), check=True)
    subprocess.run(command, cwd=str(config.root_dir), check=True)
    print(f"Packaged unsigned macOS artifact: {config.artifact_path}")
    return 0


def ditto_payload_commands(config: MacOSAppPackageConfig) -> list[list[str]]:
    return [
        ["/usr/bin/ditto", str(config.app_path), str(config.payload_path / config.app_path.name)],
        ["/usr/bin/ditto", str(config.doctor_path), str(config.payload_path / config.doctor_path.name)],
    ]


def ditto_zip_command(config: MacOSAppPackageConfig) -> list[str]:
    return [
        "/usr/bin/ditto",
        "-c",
        "-k",
        "--sequesterRsrc",
        str(config.payload_path),
        str(config.artifact_path),
    ]


if __name__ == "__main__":
    main()
