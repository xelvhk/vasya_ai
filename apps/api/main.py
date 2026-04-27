from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from apps.api.deps import require_api_key
from apps.api.rate_limit import check_http_rate_limit, resolve_client_id_from_request
from apps.api.routes import chat, events, notes, realtime, recovery, system, tasks
from utils.logger import log_interaction_event


app = FastAPI(
    title="Vasya API",
    version="0.3.0",
    description="HTTP gateway for desktop/mobile clients over Vasya core logic.",
)

app.include_router(system.router)
_secure = [Depends(require_api_key)]

app.include_router(chat.router, dependencies=_secure)
app.include_router(tasks.router, dependencies=_secure)
app.include_router(notes.router, dependencies=_secure)
app.include_router(events.router, dependencies=_secure)
app.include_router(recovery.router, dependencies=_secure)
app.include_router(realtime.router, dependencies=_secure)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = str(request.url.path)
    method = str(request.method).upper()
    if method == "POST" and path in {"/v1/chat", "/v1/pipeline"}:
        client_id = resolve_client_id_from_request(request)
        decision = check_http_rate_limit(path, client_id)
        if not decision.allowed:
            log_interaction_event(
                "api_rate_limited",
                {
                    "scope": "http",
                    "path": path,
                    "method": method,
                    "client_id": client_id,
                    "retry_after_seconds": decision.retry_after_seconds,
                },
            )
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please retry later.",
                    "retry_after_seconds": decision.retry_after_seconds,
                },
            )
            response.headers["Retry-After"] = str(decision.retry_after_seconds)
            return response
    return await call_next(request)
