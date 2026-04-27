from __future__ import annotations

import json
from pathlib import Path

from config.settings import INTEGRATIONS_STATE_FILE
from services.secret_store import get_secret, set_secret


_ALLOWED_KEYS = {
    "obsidian_vault_path",
    "github_default_repo",
    "github_api_token",
    "notion_updates_page_id",
    "notion_api_token",
    "dictation_api_url",
    "dictation_api_token",
}
_SENSITIVE_KEYS = {
    "github_api_token",
    "notion_api_token",
    "dictation_api_token",
}


def load_integration_settings() -> dict[str, str]:
    path = Path(INTEGRATIONS_STATE_FILE)
    if not path.exists():
        result: dict[str, str] = {}
        for key in _SENSITIVE_KEYS:
            value = get_secret(key)
            if value:
                result[key] = value
        return result
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    payload = _migrate_legacy_sensitive_entries(path, payload)

    result: dict[str, str] = {}
    for key, value in payload.items():
        if key not in _ALLOWED_KEYS or key in _SENSITIVE_KEYS:
            continue
        if isinstance(value, str):
            result[key] = value.strip()
    for key in _SENSITIVE_KEYS:
        secret_value = get_secret(key)
        if secret_value:
            result[key] = secret_value
    return result


def save_integration_settings(values: dict[str, str]) -> None:
    current = {
        key: value
        for key, value in load_integration_settings().items()
        if key not in _SENSITIVE_KEYS
    }
    collapse_spaces_keys = {
        "github_default_repo",
        "notion_updates_page_id",
        "dictation_api_url",
    }
    for key, value in values.items():
        if key not in _ALLOWED_KEYS:
            continue
        if key in _SENSITIVE_KEYS:
            set_secret(key, str(value).strip())
            current.pop(key, None)
            continue
        if key in collapse_spaces_keys:
            current[key] = " ".join(str(value).strip().split())
        else:
            current[key] = str(value).strip()

    path = Path(INTEGRATIONS_STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_integration_setting(key: str) -> str:
    if key not in _ALLOWED_KEYS:
        return ""
    if key in _SENSITIVE_KEYS:
        return get_secret(key)
    return load_integration_settings().get(key, "")


def _migrate_legacy_sensitive_entries(path: Path, payload: dict) -> dict:
    migrated = dict(payload)
    changed = False
    for key in _SENSITIVE_KEYS:
        raw_value = migrated.get(key)
        if not isinstance(raw_value, str) or not raw_value.strip():
            continue
        set_secret(key, raw_value.strip())
        migrated.pop(key, None)
        changed = True
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(migrated, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return migrated
