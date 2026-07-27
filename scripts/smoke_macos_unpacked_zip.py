from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_NAME = "Vasya-AI-macos-unsigned.zip"
DEFAULT_DOCTOR_TIMEOUT_SECONDS = 90.0


@dataclass(frozen=True)
class UnpackedSmokeCheck:
    name: str
    state: str
    message: str


@dataclass(frozen=True)
class MacOSUnpackedZipSmokeConfig:
    root_dir: Path
    artifact_name: str = DEFAULT_ARTIFACT_NAME
    doctor_timeout_seconds: float = DEFAULT_DOCTOR_TIMEOUT_SECONDS

    @property
    def artifact_path(self) -> Path:
        return self.root_dir / "build" / "packaging" / "release" / self.artifact_name


def main() -> None:
    args = _parse_args(sys.argv[1:])
    exit_code = run_smoke(
        MacOSUnpackedZipSmokeConfig(
            root_dir=ROOT_DIR,
            artifact_name=args.artifact_name,
            doctor_timeout_seconds=args.doctor_timeout,
        ),
    )
    raise SystemExit(exit_code)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-check the unpacked unsigned macOS ZIP artifact")
    parser.add_argument("--artifact-name", default=DEFAULT_ARTIFACT_NAME, help="ZIP artifact filename")
    parser.add_argument(
        "--doctor-timeout",
        type=float,
        default=DEFAULT_DOCTOR_TIMEOUT_SECONDS,
        help="Seconds to wait for the unpacked doctor companion",
    )
    return parser.parse_args(argv)


def run_smoke(config: MacOSUnpackedZipSmokeConfig) -> int:
    if not config.artifact_path.is_file():
        checks = [
            UnpackedSmokeCheck(
                "zip artifact",
                "FAIL",
                f"missing file: {config.artifact_path}. Run scripts/package_macos_app.py first.",
            )
        ]
    else:
        with tempfile.TemporaryDirectory(prefix="vasya-ai-zip-smoke-") as tmp:
            extract_path = Path(tmp)
            checks = unpack_zip_artifact(config, extract_path)
            if all(check.state == "OK" for check in checks):
                checks.extend(validate_unpacked_payload(extract_path))
            if all(check.state == "OK" for check in checks):
                checks.append(run_unpacked_doctor(extract_path, timeout_seconds=config.doctor_timeout_seconds))

    for check in checks:
        print(f"[{check.state}] {check.name}: {check.message}")
    return 0 if all(check.state == "OK" for check in checks) else 1


def unpack_zip_artifact(config: MacOSUnpackedZipSmokeConfig, extract_path: Path) -> list[UnpackedSmokeCheck]:
    command = ["/usr/bin/ditto", "-x", "-k", str(config.artifact_path), str(extract_path)]
    try:
        subprocess.run(command, cwd=str(config.root_dir), check=True)
    except subprocess.CalledProcessError as exc:
        return [UnpackedSmokeCheck("unzip", "FAIL", f"ditto exited with code {exc.returncode}")]
    return [UnpackedSmokeCheck("unzip", "OK", str(extract_path))]


def validate_unpacked_payload(extract_path: Path) -> list[UnpackedSmokeCheck]:
    app_path = extract_path / "Vasya AI.app"
    app_executable = app_path / "Contents" / "MacOS" / "Vasya AI"
    info_plist = app_path / "Contents" / "Info.plist"
    doctor_path = extract_path / "Vasya AI Doctor"
    doctor_executable = doctor_path / "Vasya AI Doctor"
    return [
        _path_check("app bundle", app_path, expected_kind="dir"),
        _path_check("app executable", app_executable, expected_kind="file"),
        _path_check("app Info.plist", info_plist, expected_kind="file"),
        _path_check("doctor companion", doctor_path, expected_kind="dir"),
        _path_check("doctor executable", doctor_executable, expected_kind="file"),
        _executable_check("doctor executable permissions", doctor_executable),
        _forbidden_path_check("staging wrapper", extract_path / "payload"),
    ]


def run_unpacked_doctor(extract_path: Path, *, timeout_seconds: float) -> UnpackedSmokeCheck:
    executable = extract_path / "Vasya AI Doctor" / "Vasya AI Doctor"
    try:
        result = subprocess.run(
            [str(executable), "--quiet"],
            cwd=str(extract_path),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return UnpackedSmokeCheck("doctor run", "FAIL", f"timed out after {timeout_seconds:g}s")

    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    first_line = output.splitlines()[0] if output else ""
    if result.returncode in {0, 1, 2} and "doctor result:" in output:
        return UnpackedSmokeCheck("doctor run", "OK", first_line)
    return UnpackedSmokeCheck("doctor run", "FAIL", f"exit {result.returncode}: {first_line[:240]}")


def _path_check(name: str, path: Path, *, expected_kind: str) -> UnpackedSmokeCheck:
    if expected_kind == "dir" and path.is_dir():
        return UnpackedSmokeCheck(name, "OK", str(path))
    if expected_kind == "file" and path.is_file():
        return UnpackedSmokeCheck(name, "OK", str(path))
    return UnpackedSmokeCheck(name, "FAIL", f"missing {expected_kind}: {path}")


def _executable_check(name: str, path: Path) -> UnpackedSmokeCheck:
    if path.is_file() and path.stat().st_mode & 0o111:
        return UnpackedSmokeCheck(name, "OK", str(path))
    return UnpackedSmokeCheck(name, "FAIL", f"not executable: {path}")


def _forbidden_path_check(name: str, path: Path) -> UnpackedSmokeCheck:
    if path.exists():
        return UnpackedSmokeCheck(name, "FAIL", f"unexpected path: {path}")
    return UnpackedSmokeCheck(name, "OK", f"not present: {path.name}")


if __name__ == "__main__":
    main()
