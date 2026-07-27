from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import zipfile


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_NAME = "Vasya-AI-macos-unsigned.zip"


@dataclass(frozen=True)
class ZipSmokeCheck:
    name: str
    state: str
    message: str


@dataclass(frozen=True)
class MacOSZipSmokeConfig:
    root_dir: Path
    artifact_name: str = DEFAULT_ARTIFACT_NAME

    @property
    def artifact_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "release" / self.artifact_name


def main() -> None:
    args = _parse_args(sys.argv[1:])
    exit_code = run_smoke(
        MacOSZipSmokeConfig(root_dir=ROOT_DIR, artifact_name=args.artifact_name),
    )
    raise SystemExit(exit_code)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-check the local unsigned macOS ZIP artifact")
    parser.add_argument("--artifact-name", default=DEFAULT_ARTIFACT_NAME, help="ZIP artifact filename")
    return parser.parse_args(argv)


def run_smoke(config: MacOSZipSmokeConfig) -> int:
    checks = validate_zip_artifact(config)
    for check in checks:
        print(f"[{check.state}] {check.name}: {check.message}")
    return 0 if all(check.state == "OK" for check in checks) else 1


def validate_zip_artifact(config: MacOSZipSmokeConfig) -> list[ZipSmokeCheck]:
    if not config.artifact_path.is_file():
        return [
            ZipSmokeCheck(
                "zip artifact",
                "FAIL",
                f"missing file: {config.artifact_path}. Run scripts/package_macos_app.py first.",
            )
        ]

    try:
        with zipfile.ZipFile(config.artifact_path) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile as exc:
        return [ZipSmokeCheck("zip artifact", "FAIL", f"invalid ZIP: {exc}")]

    checks = [
        ZipSmokeCheck("zip artifact", "OK", str(config.artifact_path)),
        _required_entry_check(names, "app bundle", "Vasya AI.app/"),
        _required_entry_check(names, "app executable", "Vasya AI.app/Contents/MacOS/Vasya AI"),
        _required_entry_check(names, "app Info.plist", "Vasya AI.app/Contents/Info.plist"),
        _required_entry_check(names, "app avatar assets", "Vasya AI.app/Contents/Resources/assets/"),
        _required_entry_check(names, "doctor companion", "Vasya AI Doctor/"),
        _required_entry_check(names, "doctor executable", "Vasya AI Doctor/Vasya AI Doctor"),
        _required_entry_check(names, "doctor dateparser bundle", "Vasya AI Doctor/_internal/dateparser/"),
        _forbidden_prefix_check(names, "staging wrapper", "payload/"),
    ]
    return checks


def _required_entry_check(names: set[str], name: str, entry: str) -> ZipSmokeCheck:
    if entry in names:
        return ZipSmokeCheck(name, "OK", entry)
    return ZipSmokeCheck(name, "FAIL", f"missing ZIP entry: {entry}")


def _forbidden_prefix_check(names: set[str], name: str, prefix: str) -> ZipSmokeCheck:
    matches = [item for item in names if item.startswith(prefix)]
    if not matches:
        return ZipSmokeCheck(name, "OK", f"no {prefix} entries")
    return ZipSmokeCheck(name, "FAIL", f"unexpected ZIP entry: {matches[0]}")


if __name__ == "__main__":
    main()
