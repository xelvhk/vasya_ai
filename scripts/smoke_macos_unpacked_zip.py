from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import platform
import subprocess
import sys
import tempfile


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_NAME = "Vasya-AI-macos-unsigned.zip"
DEFAULT_DOCTOR_TIMEOUT_SECONDS = 90.0
DEFAULT_OPEN_TIMEOUT_SECONDS = 5.0


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
        open_launch=args.open_launch,
        open_timeout_seconds=args.open_timeout,
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
    parser.add_argument(
        "--open-launch",
        action="store_true",
        help="Launch the unpacked .app through macOS open and watch for early crash",
    )
    parser.add_argument(
        "--open-timeout",
        type=float,
        default=DEFAULT_OPEN_TIMEOUT_SECONDS,
        help="Seconds to wait during --open-launch smoke",
    )
    return parser.parse_args(argv)


def run_smoke(
    config: MacOSUnpackedZipSmokeConfig,
    *,
    open_launch: bool = False,
    open_timeout_seconds: float = DEFAULT_OPEN_TIMEOUT_SECONDS,
) -> int:
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
            if open_launch and all(check.state == "OK" for check in checks):
                checks.append(launch_unpacked_app_with_open(extract_path, timeout_seconds=open_timeout_seconds))

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


def launch_unpacked_app_with_open(extract_path: Path, *, timeout_seconds: float) -> UnpackedSmokeCheck:
    if platform.system() != "Darwin":
        return UnpackedSmokeCheck("open launch", "FAIL", "--open-launch requires macOS")

    app_path = extract_path / "Vasya AI.app"
    process = subprocess.Popen(
        ["/usr/bin/open", "-W", str(app_path)],
        cwd=str(extract_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _request_app_quit()
        process.terminate()
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
        return UnpackedSmokeCheck("open launch", "OK", f"app stayed alive for {timeout_seconds:g}s through open")

    if process.returncode == 0:
        return UnpackedSmokeCheck("open launch", "OK", "app exited cleanly through open")

    details = _summarize_process_output(stdout, stderr)
    return UnpackedSmokeCheck("open launch", "FAIL", f"open exited with code {process.returncode}{details}")


def _request_app_quit() -> None:
    try:
        subprocess.run(
            ["/usr/bin/osascript", "-e", 'tell application "Vasya AI" to quit'],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        pass


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


def _summarize_process_output(stdout: str, stderr: str) -> str:
    output = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    if not output:
        return ""
    first_line = output.splitlines()[0]
    return f": {first_line[:240]}"


if __name__ == "__main__":
    main()
