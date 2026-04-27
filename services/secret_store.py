from __future__ import annotations

import json
import os
from pathlib import Path

from config.settings import INTEGRATIONS_SECRETS_FILE

_SERVICE_NAME = "vasya_ai"


def get_secret(key: str) -> str:
    normalized_key = _normalize_key(key)
    if not normalized_key:
        return ""

    keyring_backend = _keyring_backend()
    if keyring_backend is not None:
        try:
            value = keyring_backend.get_password(_SERVICE_NAME, normalized_key)
            return str(value or "").strip()
        except Exception:
            return ""
    return _load_file_secrets().get(normalized_key, "")


def set_secret(key: str, value: str) -> None:
    normalized_key = _normalize_key(key)
    if not normalized_key:
        return
    normalized_value = str(value or "").strip()

    keyring_backend = _keyring_backend()
    if keyring_backend is not None:
        try:
            if normalized_value:
                keyring_backend.set_password(_SERVICE_NAME, normalized_key, normalized_value)
            else:
                keyring_backend.delete_password(_SERVICE_NAME, normalized_key)
            return
        except Exception:
            pass

    payload = _load_file_secrets()
    if normalized_value:
        payload[normalized_key] = normalized_value
    else:
        payload.pop(normalized_key, None)
    _save_file_secrets(payload)


def _keyring_backend():
    try:
        import keyring
    except Exception:
        return None
    return keyring


def _load_file_secrets() -> dict[str, str]:
    path = Path(INTEGRATIONS_SECRETS_FILE)
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
        if not isinstance(key, str):
            continue
        if isinstance(value, str) and value.strip():
            result[key.strip()] = value.strip()
    return result


def _save_file_secrets(payload: dict[str, str]) -> None:
    path = Path(INTEGRATIONS_SECRETS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _normalize_key(key: str) -> str:
    return " ".join(str(key or "").strip().split())
