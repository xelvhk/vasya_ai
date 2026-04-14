from __future__ import annotations

from fastapi import Header, HTTPException

from config.settings import VASYA_API_AUTH_TOKEN


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    # If token is not set, API stays open for local/dev usage.
    if not VASYA_API_AUTH_TOKEN:
        return
    if x_api_key == VASYA_API_AUTH_TOKEN:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key.")

