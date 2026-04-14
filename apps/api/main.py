from __future__ import annotations

from fastapi import Depends, FastAPI

from apps.api.deps import require_api_key
from apps.api.routes import chat, events, notes, recovery, system, tasks


app = FastAPI(
    title="Vasya API",
    version="0.2.0",
    description="HTTP gateway for desktop/mobile clients over Vasya core logic.",
)

app.include_router(system.router)
_secure = [Depends(require_api_key)]

app.include_router(chat.router, dependencies=_secure)
app.include_router(tasks.router, dependencies=_secure)
app.include_router(notes.router, dependencies=_secure)
app.include_router(events.router, dependencies=_secure)
app.include_router(recovery.router, dependencies=_secure)
