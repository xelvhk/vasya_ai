from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any

from config.settings import (
    API_RATE_LIMIT_CHAT_MAX,
    API_RATE_LIMIT_ENABLED,
    API_RATE_LIMIT_MORNING_BRIEF_MAX,
    API_RATE_LIMIT_PIPELINE_MAX,
    API_RATE_LIMIT_WINDOW_SECONDS,
    API_RATE_LIMIT_WS_CONNECTIONS_MAX,
    API_RATE_LIMIT_WS_MESSAGES_MAX,
)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


_LOCK = Lock()
_HTTP_BUCKETS: dict[tuple[str, str], deque[float]] = {}
_WS_MESSAGE_BUCKETS: dict[str, deque[float]] = {}
_WS_CONNECTION_COUNTS: dict[str, int] = {}


def resolve_client_id_from_request(request: Any) -> str:
    forwarded = _read_forwarded_for(getattr(request, "headers", None))
    if forwarded:
        return forwarded
    client = getattr(request, "client", None)
    host = getattr(client, "host", "") if client is not None else ""
    host_text = str(host).strip()
    return host_text or "unknown"


def resolve_client_id_from_websocket(websocket: Any) -> str:
    forwarded = _read_forwarded_for(getattr(websocket, "headers", None))
    if forwarded:
        return forwarded
    client = getattr(websocket, "client", None)
    host = getattr(client, "host", "") if client is not None else ""
    host_text = str(host).strip()
    return host_text or "unknown"


def check_http_rate_limit(path: str, client_id: str, *, now: float | None = None) -> RateLimitDecision:
    if not API_RATE_LIMIT_ENABLED:
        return RateLimitDecision(True, 0)
    limit = _http_limit_for_path(path)
    if limit <= 0:
        return RateLimitDecision(True, 0)
    window_seconds = max(1, API_RATE_LIMIT_WINDOW_SECONDS)
    return _check_bucket(
        storage=_HTTP_BUCKETS,
        key=(client_id, path),
        limit=limit,
        window_seconds=window_seconds,
        now=now,
    )


def register_ws_connection(client_id: str, *, now: float | None = None) -> RateLimitDecision:
    del now  # reserved for future policy evolution
    if not API_RATE_LIMIT_ENABLED:
        return RateLimitDecision(True, 0)
    limit = max(1, API_RATE_LIMIT_WS_CONNECTIONS_MAX)
    with _LOCK:
        current = _WS_CONNECTION_COUNTS.get(client_id, 0)
        if current >= limit:
            return RateLimitDecision(False, retry_after_seconds=1)
        _WS_CONNECTION_COUNTS[client_id] = current + 1
    return RateLimitDecision(True, 0)


def unregister_ws_connection(client_id: str) -> None:
    with _LOCK:
        current = _WS_CONNECTION_COUNTS.get(client_id, 0)
        if current <= 1:
            _WS_CONNECTION_COUNTS.pop(client_id, None)
            return
        _WS_CONNECTION_COUNTS[client_id] = current - 1


def check_ws_message_rate_limit(client_id: str, *, now: float | None = None) -> RateLimitDecision:
    if not API_RATE_LIMIT_ENABLED:
        return RateLimitDecision(True, 0)
    limit = max(1, API_RATE_LIMIT_WS_MESSAGES_MAX)
    window_seconds = max(1, API_RATE_LIMIT_WINDOW_SECONDS)
    return _check_bucket(
        storage=_WS_MESSAGE_BUCKETS,
        key=client_id,
        limit=limit,
        window_seconds=window_seconds,
        now=now,
    )


def _check_bucket(
    *,
    storage: dict[Any, deque[float]],
    key: Any,
    limit: int,
    window_seconds: int,
    now: float | None = None,
) -> RateLimitDecision:
    ts_now = float(now if now is not None else time.time())
    cutoff = ts_now - float(window_seconds)
    with _LOCK:
        bucket = storage.get(key)
        if bucket is None:
            bucket = deque()
            storage[key] = bucket
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (ts_now - bucket[0])))
            return RateLimitDecision(False, retry_after)
        bucket.append(ts_now)
    return RateLimitDecision(True, 0)


def _http_limit_for_path(path: str) -> int:
    normalized = str(path or "").strip().lower()
    if normalized.endswith("/chat"):
        return max(1, API_RATE_LIMIT_CHAT_MAX)
    if normalized.endswith("/pipeline"):
        return max(1, API_RATE_LIMIT_PIPELINE_MAX)
    if normalized.endswith("/morning-brief"):
        return max(1, API_RATE_LIMIT_MORNING_BRIEF_MAX)
    return 0


def _read_forwarded_for(headers: Any) -> str:
    if headers is None:
        return ""
    raw = ""
    try:
        raw = str(headers.get("x-forwarded-for", "")).strip()
    except Exception:
        raw = ""
    if not raw:
        return ""
    first = raw.split(",", maxsplit=1)[0].strip()
    return first
