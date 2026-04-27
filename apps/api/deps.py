from __future__ import annotations

import secrets

from fastapi import Header, HTTPException
from fastapi import WebSocket

from config.settings import (
    VASYA_API_ALLOW_QUERY_TOKEN,
    VASYA_API_AUTH_TOKEN,
    VASYA_API_REQUIRE_AUTH,
)


def require_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    if not VASYA_API_REQUIRE_AUTH:
        return
    if not VASYA_API_AUTH_TOKEN:
        raise HTTPException(status_code=503, detail="API auth token is not configured.")

    candidate = (x_api_key or "").strip() or _extract_bearer_token(authorization)
    if candidate and secrets.compare_digest(candidate, VASYA_API_AUTH_TOKEN):
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def is_ws_authorized(websocket: WebSocket) -> bool:
    if not VASYA_API_REQUIRE_AUTH:
        return True
    if not VASYA_API_AUTH_TOKEN:
        return False

    header_token = (websocket.headers.get("x-api-key") or "").strip()
    bearer_token = _extract_bearer_token(websocket.headers.get("authorization"))
    candidates = [token for token in (header_token, bearer_token) if token]
    if VASYA_API_ALLOW_QUERY_TOKEN:
        query_token = (websocket.query_params.get("api_key") or "").strip()
        if query_token:
            candidates.append(query_token)
    return any(secrets.compare_digest(token, VASYA_API_AUTH_TOKEN) for token in candidates)


def _extract_bearer_token(authorization: str | None) -> str:
    value = (authorization or "").strip()
    if not value:
        return ""
    parts = value.split(None, 1)
    if len(parts) != 2:
        return ""
    scheme, token = parts[0].lower(), parts[1].strip()
    if scheme != "bearer" or not token:
        return ""
    return token
