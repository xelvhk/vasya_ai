from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import plistlib
from pathlib import Path
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_APP_NAME = "Vasya AI"


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    state: str
    message: str


@dataclass(frozen=True)
class MacOSAppSmokeConfig:
    root_dir: Path
    app_name: str = DEFAULT_APP_NAME

    @property
    def app_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "dist" / f"{self.app_name}.app"

    @property
    def executable_path(self) -> Path:
        return self.app_path / "Contents" / "MacOS" / self.app_name

    @property
    def info_plist_path(self) -> Path:
        return self.app_path / "Contents" / "Info.plist"

    @property
    def resources_path(self) -> Path:
        return self.app_path / "Contents" / "Resources"


def main() -> None:
    args = _parse_args(sys.argv[1:])
    exit_code = run_smoke(
        MacOSAppSmokeConfig(root_dir=ROOT_DIR, app_name=args.name),
        launch=args.launch,
        timeout_seconds=args.timeout,
        offscreen=args.offscreen,
    )
    raise SystemExit(exit_code)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-check a local unsigned macOS .app prototype")
    parser.add_argument("--name", default=DEFAULT_APP_NAME, help="macOS app bundle display name")
    parser.add_argument("--launch", action="store_true", help="Launch the bundled executable and watch for early crash")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait during --launch smoke")
    parser.add_argument("--offscreen", action="store_true", help="Set QT_QPA_PLATFORM=offscreen during --launch")
    return parser.parse_args(argv)


def run_smoke(
    config: MacOSAppSmokeConfig,
    *,
    launch: bool = False,
    timeout_seconds: float = 5.0,
    offscreen: bool = False,
) -> int:
    checks = validate_app_bundle(config)
    if launch and all(check.state == "OK" for check in checks):
        checks.append(launch_app_executable(config, timeout_seconds=timeout_seconds, offscreen=offscreen))

    for check in checks:
        print(f"[{check.state}] {check.name}: {check.message}")

    return 0 if all(check.state == "OK" for check in checks) else 1


def validate_app_bundle(config: MacOSAppSmokeConfig) -> list[SmokeCheck]:
    checks = [
        _path_check("app bundle", config.app_path, expected_kind="dir"),
        _path_check("Info.plist", config.info_plist_path, expected_kind="file"),
        _path_check("app executable", config.executable_path, expected_kind="file"),
        _path_check("resources", config.resources_path, expected_kind="dir"),
        _path_check("avatar assets", config.resources_path / "assets", expected_kind="dir"),
        _path_check("avatar skins", config.resources_path / "assets" / "skins", expected_kind="dir"),
    ]

    if config.info_plist_path.is_file():
        checks.extend(_plist_checks(config))

    if config.executable_path.is_file() and not os.access(config.executable_path, os.X_OK):
        checks.append(SmokeCheck("app executable permissions", "FAIL", "executable is not marked runnable"))

    return checks


def launch_app_executable(
    config: MacOSAppSmokeConfig,
    *,
    timeout_seconds: float,
    offscreen: bool,
) -> SmokeCheck:
    env = dict(os.environ)
    if offscreen:
        env["QT_QPA_PLATFORM"] = "offscreen"

    process = subprocess.Popen(
        [str(config.executable_path)],
        cwd=str(config.root_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        return SmokeCheck("launch", "OK", f"app stayed alive for {timeout_seconds:g}s")

    if process.returncode == 0:
        return SmokeCheck("launch", "OK", "app exited cleanly during launch smoke")

    details = _summarize_process_output(stdout, stderr)
    return SmokeCheck("launch", "FAIL", f"app exited with code {process.returncode}{details}")


def _path_check(name: str, path: Path, *, expected_kind: str) -> SmokeCheck:
    if expected_kind == "dir" and path.is_dir():
        return SmokeCheck(name, "OK", str(path))
    if expected_kind == "file" and path.is_file():
        return SmokeCheck(name, "OK", str(path))
    return SmokeCheck(name, "FAIL", f"missing {expected_kind}: {path}")


def _plist_checks(config: MacOSAppSmokeConfig) -> list[SmokeCheck]:
    try:
        with config.info_plist_path.open("rb") as file:
            plist = plistlib.load(file)
    except (OSError, plistlib.InvalidFileException) as exc:
        return [SmokeCheck("Info.plist parse", "FAIL", str(exc))]

    return [
        _plist_value_check(plist, "CFBundlePackageType", "APPL"),
        _plist_value_check(plist, "CFBundleExecutable", config.app_name),
        _plist_value_check(plist, "CFBundleDisplayName", config.app_name),
    ]


def _plist_value_check(plist: dict, key: str, expected: str) -> SmokeCheck:
    actual = plist.get(key)
    if actual == expected:
        return SmokeCheck(key, "OK", str(actual))
    return SmokeCheck(key, "FAIL", f"expected {expected!r}, got {actual!r}")


def _summarize_process_output(stdout: str, stderr: str) -> str:
    output = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    if not output:
        return ""
    first_line = output.splitlines()[0]
    return f": {first_line[:240]}"


if __name__ == "__main__":
    main()
