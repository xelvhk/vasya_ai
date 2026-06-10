from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
import json
import os
import platform
import shutil
import sqlite3
import sys
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config.settings import (  # noqa: E402
    GOOGLE_CALENDAR_CREDENTIALS_FILE,
    GOOGLE_CALENDAR_ENABLED,
    GOOGLE_CALENDAR_TOKEN_FILE,
    MEMORY_WIKI_DIR,
    OLLAMA_MODEL,
    OLLAMA_URL,
    STORAGE_DB_FILE,
    VASYA_API_AUTH_TOKEN,
    VASYA_API_REQUIRE_AUTH,
)
from utils.platform_runtime import get_platform_name  # noqa: E402


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str
    fix: str | None = None


def main() -> None:
    args = _parse_args(sys.argv[1:])
    exit_code = run_doctor(
        json_output=args.json,
        strict=args.strict,
        quiet=args.quiet,
    )
    sys.exit(exit_code)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vasya AI environment diagnostics")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat WARN as failure (exit code 1)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only summary (ignored when --json is enabled)",
    )
    return parser.parse_args(argv)


def run_doctor(*, json_output: bool = False, strict: bool = False, quiet: bool = False) -> int:
    results = run_checks()
    summary = _build_summary(results)
    exit_code = _resolve_exit_code(results, strict=strict)

    if json_output:
        payload = {
            "platform": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "strict": bool(strict),
            "quiet": bool(quiet),
            "summary": summary,
            "exit_code": exit_code,
            "checks": [
                {
                    "name": result.name,
                    "status": result.status,
                    "message": result.message,
                    "fix": result.fix,
                }
                for result in results
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return exit_code

    if not quiet:
        print("== Vasya AI doctor ==")
        print(f"platform: {platform.system()} {platform.release()}")
        print(f"python: {platform.python_version()}")
        print()
        for result in results:
            _print_result(result)
            print()
    print(summary)
    return exit_code


def run_checks() -> list[CheckResult]:
    checks = [
        check_env_file,
        check_virtualenv,
        check_python_modules,
        check_ollama_binary,
        check_ollama_server,
        check_storage,
        check_memory_wiki_dir,
        check_api_auth_config,
        check_google_calendar,
        check_autostart,
    ]
    return [check() for check in checks]


def check_env_file() -> CheckResult:
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        return report("env file", "OK", f"found .env at {env_path}")
    if _is_ci_environment():
        return report("env file", "OK", ".env is not required in CI smoke checks")
    return report(
        "env file",
        "WARN",
        f".env is missing at {env_path}",
        fix="Copy .env.example to .env and adjust local values.",
    )


def check_virtualenv() -> CheckResult:
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if _is_ci_environment() and not in_venv:
        return report("virtualenv", "OK", "CI uses GitHub Actions managed Python")
    return report(
        "virtualenv",
        "OK" if in_venv else "WARN",
        "virtual environment is active" if in_venv else "virtual environment is not active",
        fix=None if in_venv else "Activate environment: source .venv/bin/activate",
    )


def check_python_modules() -> CheckResult:
    modules = [
        "faster_whisper",
        "sounddevice",
        "scipy",
        "pydantic",
        "dateparser",
        "googleapiclient",
        "google_auth_oauthlib",
    ]
    missing = []
    for module_name in modules:
        try:
            importlib.import_module(module_name)
        except Exception:
            missing.append(module_name)

    if missing:
        return report(
            "python dependencies",
            "FAIL",
            f"missing modules: {', '.join(missing)}",
            fix="Install dependencies: pip install -r requirements.txt",
        )
    return report("python dependencies", "OK", "core modules are available")


def check_ollama_binary() -> CheckResult:
    found = shutil.which("ollama") is not None
    if _is_ci_environment() and not found:
        return report("ollama binary", "OK", "Ollama binary is not required for CI smoke checks")
    return report(
        "ollama binary",
        "OK" if found else "FAIL",
        "ollama command found" if found else "ollama command not found",
        fix=None if found else "Install Ollama from https://ollama.com/download",
    )


def check_ollama_server() -> CheckResult:
    if _is_ci_environment():
        return report("ollama server", "OK", "Ollama server check skipped in CI")
    try:
        response = requests.get(_healthcheck_url(), timeout=2)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return report(
            "ollama server",
            "WARN",
            f"cannot reach Ollama: {exc}",
            fix="Start local server: ollama serve",
        )

    models = [item.get("name", "") for item in payload.get("models", [])]
    has_model = any(name.startswith(OLLAMA_MODEL) for name in models)
    if has_model:
        return report("ollama server", "OK", f"Ollama is up and model '{OLLAMA_MODEL}' is available")
    return report(
        "ollama server",
        "WARN",
        f"Ollama is up but model '{OLLAMA_MODEL}' is not available",
        fix=f"Pull model: ollama pull {OLLAMA_MODEL}",
    )


def check_storage() -> CheckResult:
    db_path = Path(STORAGE_DB_FILE)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.execute("SELECT 1")
    except Exception as exc:
        return report("storage", "FAIL", f"cannot open SQLite storage: {exc}")

    return report("storage", "OK", f"SQLite storage is accessible at {db_path}")


def check_memory_wiki_dir() -> CheckResult:
    wiki_dir = Path(MEMORY_WIKI_DIR).expanduser()
    try:
        wiki_dir.mkdir(parents=True, exist_ok=True)
        probe = wiki_dir / ".doctor-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as exc:
        return report("memory wiki path", "FAIL", f"cannot write memory wiki directory: {exc}")
    return report("memory wiki path", "OK", f"memory wiki is writable at {wiki_dir}")


def check_api_auth_config() -> CheckResult:
    if not VASYA_API_REQUIRE_AUTH:
        return report(
            "api auth config",
            "WARN",
            "VASYA_API_REQUIRE_AUTH is disabled",
            fix="Set VASYA_API_REQUIRE_AUTH=true for secure default.",
        )
    if not VASYA_API_AUTH_TOKEN:
        return report(
            "api auth config",
            "FAIL",
            "VASYA_API_REQUIRE_AUTH=true but VASYA_API_AUTH_TOKEN is empty",
            fix="Set VASYA_API_AUTH_TOKEN in .env before exposing API.",
        )
    return report("api auth config", "OK", "API auth token is configured")


def check_google_calendar() -> CheckResult:
    if not GOOGLE_CALENDAR_ENABLED:
        return report("google calendar", "OK", "integration is disabled")

    credentials_exists = Path(GOOGLE_CALENDAR_CREDENTIALS_FILE).exists()
    token_exists = Path(GOOGLE_CALENDAR_TOKEN_FILE).exists()

    if credentials_exists and token_exists:
        return report("google calendar", "OK", "credentials and token are present")
    if credentials_exists:
        return report("google calendar", "WARN", "credentials present, token not created yet")
    return report(
        "google calendar",
        "WARN",
        f"credentials file not found: {GOOGLE_CALENDAR_CREDENTIALS_FILE}",
        fix="Place OAuth credentials file or disable GOOGLE_CALENDAR_ENABLED.",
    )


def check_autostart() -> CheckResult:
    if get_platform_name() != "macos":
        return report("autostart", "OK", "not applicable on this platform")

    try:
        from scripts.autostart_macos import is_autostart_enabled
    except Exception as exc:
        return report("autostart", "WARN", f"cannot inspect autostart: {exc}")

    enabled = is_autostart_enabled()
    return report(
        "autostart",
        "OK",
        "launch at login is enabled" if enabled else "launch at login is disabled",
    )


def report(name: str, status: str, message: str, *, fix: str | None = None) -> CheckResult:
    normalized_status = status.strip().upper()
    if normalized_status not in {"OK", "WARN", "FAIL"}:
        raise ValueError(f"unsupported status: {status}")
    return CheckResult(name=name, status=normalized_status, message=message, fix=fix)


def _print_result(result: CheckResult) -> None:
    print(f"[{result.status}] {result.name}: {result.message}")
    if result.fix and result.status in {"WARN", "FAIL"}:
        print(f"  Fix: {result.fix}")


def _build_summary(results: list[CheckResult]) -> str:
    total = len(results)
    ok_count = sum(1 for result in results if result.status == "OK")
    warn_count = sum(1 for result in results if result.status == "WARN")
    fail_count = sum(1 for result in results if result.status == "FAIL")
    if fail_count:
        state = "issues found"
    elif warn_count:
        state = "warnings found"
    else:
        state = "all key checks passed"
    return (
        f"doctor result: {state} "
        f"(ok={ok_count}, warn={warn_count}, fail={fail_count}, total={total})"
    )


def _resolve_exit_code(results: list[CheckResult], *, strict: bool) -> int:
    has_failures = any(result.status == "FAIL" for result in results)
    has_warnings = any(result.status == "WARN" for result in results)
    if has_failures:
        return 1
    if has_warnings:
        return 1 if strict else 2
    return 0


def _healthcheck_url() -> str:
    base_url = OLLAMA_URL.rsplit("/", 1)[0]
    return f"{base_url}/tags"


def _is_ci_environment() -> bool:
    return str(os.getenv("CI", "")).strip().lower() in {"1", "true", "yes"}


if __name__ == "__main__":
    main()
