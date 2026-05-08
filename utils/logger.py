from __future__ import annotations

import json
import re
import uuid
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path

from config.settings import (
    INTERACTION_LOG_FILE,
    LOG_INCLUDE_TEXT_CONTENT,
    LOG_MAX_FIELD_LENGTH,
    LOG_REDACT_SENSITIVE,
    VOICE_LOG_FILE,
)

_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)
_SESSION_ID: ContextVar[str | None] = ContextVar("session_id", default=None)


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[LOG {timestamp}] {message}"
    print(line)


def log_voice_event(message: str) -> None:
    _append_line(VOICE_LOG_FILE, "VOICE", message)


def log_interaction_event(event_type: str, payload: dict) -> None:
    safe_payload = _sanitize_payload(payload)
    request_id = safe_payload.get("request_id") or _REQUEST_ID.get() or _new_request_id()
    session_id = safe_payload.get("session_id") or _SESSION_ID.get() or _new_session_id()
    enriched_payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": event_type,
        "request_id": request_id,
        "session_id": session_id,
        **safe_payload,
    }
    line = json.dumps(enriched_payload, ensure_ascii=False)
    print(f"[INTERACTION] {line}")
    _append_raw_line(INTERACTION_LOG_FILE, line)


def set_logging_context(*, request_id: str | None = None, session_id: str | None = None) -> None:
    if request_id is not None:
        _REQUEST_ID.set(request_id)
    if session_id is not None:
        _SESSION_ID.set(session_id)


def start_logging_scope(*, session_id: str | None = None) -> tuple[str, str]:
    request_id = _new_request_id()
    scoped_session_id = session_id or _new_session_id()
    _REQUEST_ID.set(request_id)
    _SESSION_ID.set(scoped_session_id)
    return request_id, scoped_session_id


def get_logging_context() -> tuple[str, str]:
    request_id = _REQUEST_ID.get() or _new_request_id()
    session_id = _SESSION_ID.get() or _new_session_id()
    _REQUEST_ID.set(request_id)
    _SESSION_ID.set(session_id)
    return request_id, session_id


def _append_line(path_str: str, prefix: str, message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{prefix} {timestamp}] {message}"
    print(line)
    _append_raw_line(path_str, line)


def _append_raw_line(path_str: str, line: str) -> None:
    log_path = Path(path_str)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(line + "\n")


_SENSITIVE_KEY_MARKERS = (
    "token",
    "password",
    "secret",
    "authorization",
    "api_key",
    "x_api_key",
)
_TEXTUAL_PRIVACY_KEYS = {"user_text", "response", "text", "prompt", "input"}
_BEARER_RE = re.compile(r"^\s*bearer\s+.+$", re.IGNORECASE)


def _sanitize_payload(payload: dict) -> dict:
    if not LOG_REDACT_SENSITIVE:
        return payload
    return _sanitize_value(payload, key_hint=None)


def _sanitize_value(value, key_hint: str | None):
    if isinstance(value, dict):
        result = {}
        for key, nested in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                result[key_text] = _mask_secret(str(nested))
            else:
                result[key_text] = _sanitize_value(nested, key_hint=key_text)
        return result

    if isinstance(value, list):
        return [_sanitize_value(item, key_hint=key_hint) for item in value]

    if isinstance(value, tuple):
        return [_sanitize_value(item, key_hint=key_hint) for item in value]

    if isinstance(value, str):
        if key_hint and _is_sensitive_key(key_hint):
            return _mask_secret(value)
        if _looks_like_secret(value):
            return _mask_secret(value)
        if key_hint and key_hint.lower() in _TEXTUAL_PRIVACY_KEYS and not LOG_INCLUDE_TEXT_CONTENT:
            return _mask_text(value)
        return _truncate(value)

    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_").strip()
    if normalized in _SENSITIVE_KEY_MARKERS:
        return True
    return any(marker in normalized for marker in _SENSITIVE_KEY_MARKERS)


def _looks_like_secret(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if _BEARER_RE.match(text):
        return True
    if len(text) >= 32 and re.fullmatch(r"[A-Za-z0-9_\-\.=]+", text) is not None:
        return True
    return False


def _mask_secret(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return ""
    return "<redacted_secret>"


def _mask_text(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    return f"<redacted_text:{len(text)} chars>"


def _truncate(value: str) -> str:
    limit = max(80, LOG_MAX_FIELD_LENGTH)
    if len(value) <= limit:
        return value
    return f"{value[:limit-3]}..."


def _new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:10]}"


def _new_session_id() -> str:
    return f"sess-{uuid.uuid4().hex[:10]}"
