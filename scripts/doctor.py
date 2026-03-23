from __future__ import annotations

import importlib
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
    OLLAMA_MODEL,
    OLLAMA_URL,
    STORAGE_DB_FILE,
)


def main() -> None:
    print("== Vasya AI doctor ==")
    print(f"platform: {platform.system()} {platform.release()}")
    print(f"python: {platform.python_version()}")
    print()

    checks = [
        check_virtualenv,
        check_python_modules,
        check_ollama_binary,
        check_ollama_server,
        check_storage,
        check_google_calendar,
    ]

    failed = False
    for check in checks:
        ok = check()
        failed = failed or not ok
        print()

    if failed:
        print("doctor result: issues found")
        sys.exit(1)

    print("doctor result: all key checks passed")


def check_virtualenv() -> bool:
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    return report(
        "virtualenv",
        in_venv,
        "virtual environment is active" if in_venv else "virtual environment is not active",
    )


def check_python_modules() -> bool:
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
            False,
            f"missing modules: {', '.join(missing)}",
        )
    return report("python dependencies", True, "core modules are available")


def check_ollama_binary() -> bool:
    found = shutil.which("ollama") is not None
    return report(
        "ollama binary",
        found,
        "ollama command found" if found else "ollama command not found",
    )


def check_ollama_server() -> bool:
    try:
        response = requests.get(_healthcheck_url(), timeout=2)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return report("ollama server", False, f"cannot reach Ollama: {exc}")

    models = [item.get("name", "") for item in payload.get("models", [])]
    has_model = any(name.startswith(OLLAMA_MODEL) for name in models)
    if has_model:
        return report("ollama server", True, f"Ollama is up and model '{OLLAMA_MODEL}' is available")
    return report(
        "ollama server",
        False,
        f"Ollama is up but model '{OLLAMA_MODEL}' is not available",
    )


def check_storage() -> bool:
    db_path = Path(STORAGE_DB_FILE)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.execute("SELECT 1")
    except Exception as exc:
        return report("storage", False, f"cannot open SQLite storage: {exc}")

    return report("storage", True, f"SQLite storage is accessible at {db_path}")


def check_google_calendar() -> bool:
    if not GOOGLE_CALENDAR_ENABLED:
        return report("google calendar", True, "integration is disabled")

    credentials_exists = Path(GOOGLE_CALENDAR_CREDENTIALS_FILE).exists()
    token_exists = Path(GOOGLE_CALENDAR_TOKEN_FILE).exists()

    if credentials_exists and token_exists:
        return report("google calendar", True, "credentials and token are present")
    if credentials_exists:
        return report("google calendar", True, "credentials present, token not created yet")
    return report(
        "google calendar",
        False,
        f"credentials file not found: {GOOGLE_CALENDAR_CREDENTIALS_FILE}",
    )


def report(name: str, ok: bool, message: str) -> bool:
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {name}: {message}")
    return ok


def _healthcheck_url() -> str:
    base_url = OLLAMA_URL.rsplit("/", 1)[0]
    return f"{base_url}/tags"


if __name__ == "__main__":
    main()
