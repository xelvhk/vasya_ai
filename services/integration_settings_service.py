from __future__ import annotations

import json
from pathlib import Path

from config.settings import INTEGRATIONS_STATE_FILE


_ALLOWED_KEYS = {
    "github_default_repo",
    "github_api_token",
    "notion_updates_page_id",
    "notion_api_token",
}


def load_integration_settings() -> dict[str, str]:
    path = Path(INTEGRATIONS_STATE_FILE)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    result: dict[str, str] = {}
    for key, value in payload.items():
        if key not in _ALLOWED_KEYS:
            continue
        if isinstance(value, str):
            result[key] = value.strip()
    return result


def save_integration_settings(values: dict[str, str]) -> None:
    current = load_integration_settings()
    for key, value in values.items():
        if key not in _ALLOWED_KEYS:
            continue
        current[key] = " ".join(str(value).strip().split()) if key in {
            "github_default_repo",
            "notion_updates_page_id",
        } else str(value).strip()

    path = Path(INTEGRATIONS_STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_integration_setting(key: str) -> str:
    if key not in _ALLOWED_KEYS:
        return ""
    return load_integration_settings().get(key, "")
