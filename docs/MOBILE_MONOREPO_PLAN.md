# Mobile Monorepo Plan (Phase 1)

Goal: keep one repository and add a mobile-ready API surface without breaking the current desktop flow.

## Target shape

```text
apps/
  api/        # FastAPI gateway for mobile/web clients
scripts/      # desktop shell and local runtime scripts
core/         # routing and orchestration
services/     # domain + integration services
repositories/ # local persistence
```

## Phase 1 (landed)

- Added `apps/api/main.py` with baseline endpoints:
  - `GET /health`
  - `POST /v1/chat`
  - `GET/POST /v1/tasks`
  - `GET/POST /v1/notes`
  - `GET/POST /v1/events`
  - `POST /v1/recovery/mic-test`
  - `POST /v1/recovery/auto-tune`
- Added API dependencies: `fastapi`, `uvicorn`.

## Phase 2 (next)

1. Extract API schemas into `apps/api/schemas.py`.
2. Split routes into modules: `chat.py`, `tasks.py`, `notes.py`, `events.py`, `recovery.py`.
3. Add API-level auth switch (optional token in `.env`).
4. Add integration tests for API endpoints.

## Phase 3 (mobile start)

1. Create `apps/mobile` (React Native or Flutter).
2. Connect to `apps/api` endpoints for:
   - chat
   - tasks/notes/events
   - recovery commands
3. Ship push-to-talk and text input first, then advanced voice UX.
