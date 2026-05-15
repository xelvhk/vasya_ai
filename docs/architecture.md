# Vasya AI Architecture

## Overview

Vasya AI is a local-first voice assistant with modular routing, domain tools, and optional integrations.

Core flow:

`Input (voice/text) -> intent/routing -> tool/agent execution -> response (text/voice) -> logs/metrics`

## Layer model

### 1) Entry points

- `main.py`
- desktop shell: `scripts/avatar_widget.py`, `scripts/hotkey_daemon.py`
- API gateway: `apps/api/*` (HTTP + WebSocket)

Responsibilities:
- accept user input
- start interaction/session
- return output to UI/client

### 2) Orchestration and routing

- `core/orchestrator.py`
- `core/router.py`
- `core/tools.py`
- `core/agent_policy.py`
- `core/handoffs.py`

Responsibilities:
- classify and route intents
- apply state-aware precedence (confirmations, game mode, etc.)
- dispatch intent to correct tool/service

### 3) Domain behaviors

- `agents/task_agent.py`
- `agents/calendar_agent.py`
- `agents/note_agent.py`
- `agents/game_agent.py`

Responsibilities:
- business logic for task/calendar/notes/game workflows
- user-facing response formatting

### 4) Services and adapters

- service layer: `services/*`
- repository layer: `repositories/*`
- integration adapters: Notion/GitHub/Obsidian/Google Calendar
- OS actions: `services/os_action_service.py`

Responsibilities:
- concrete operations (read/write, sync, import/export)
- external I/O and adapter-specific rules

### 5) Voice and runtime pipeline

- `voice/session.py`
- `voice/pipeline.py`
- `voice/stt.py`
- `voice/tts.py`
- `voice/backend_registry.py`

Responsibilities:
- capture/transcribe audio
- run low-latency interaction loop
- support fast-path replies and interruption logic

## Data model and storage

Primary local storage:
- SQLite (`storage/vasya.db`) for core operational data
- local state files (`storage/*.json`) for runtime/session settings

Operational logs:
- interaction log (`storage/interactions.log`)
- voice log (`storage/voice.log`)

Knowledge/memory adapters:
- Obsidian vault (local files)
- Notion (optional remote adapter)

Memory Center baseline:
- `memory_sources` tracks connected/local sources by stable `source_key`
- `memory_chunks` stores provenance-backed memory leaves and points to Markdown artifacts
- `memory_sync_state` tracks per `(toolkit, connection_id)` cursors and sync timing
- `services/memory_center_service.py` owns ingest/status/recent/search/digest/sync-state behavior
- `services/memory_sync_service.py` connects GitHub, Notion, and Obsidian adapters to memory ingest
- `services/memory_scheduler_service.py` runs periodic non-forced sync in the desktop process
- `apps/api/routes/memory.py` exposes `/v1/memory/status`, `/v1/memory/recent`, `/v1/memory/search`, `/v1/memory/digest`, and `/v1/memory/sync` for desktop/mobile clients
- `scripts/avatar_widget.py` exposes Memory Center status, recent, search, daily digest, and manual sync in the desktop/tray menu
- `utils/intent_fastpaths.py` and `core/tools.py` expose fast voice/text Memory Center commands

This is intentionally a thin local-first foundation rather than a full vector store. Daily digest artifacts provide deterministic, inspectable Markdown summaries before adding LLM-based synthesis, entity/topic extraction, and Obsidian navigation.

## API surface

Main API module: `apps/api/main.py`

Key routes:
- system: `/health`, `/health/live`, `/health/ready`
- chat/pipeline: `/v1/chat`, `/v1/pipeline`
- realtime: `/v1/ws/voice`
- tasks/notes/events/recovery
- memory center: `/v1/memory/status`, `/v1/memory/recent`, `/v1/memory/search`, `/v1/memory/digest`, `/v1/memory/sync`

Security baseline:
- token auth for `/v1/*` (default on)
- HTTP + WS throttling
- sensitive log redaction

## Dependency rules

See ADR:
- `docs/adr/ADR-001-layering-and-dependencies.md`

Practical constraints:
- core orchestration should not depend on UI/transport details
- adapters isolate external SDK/API specifics
- new integrations should enter via service/adapter boundary

## Request/session observability

Interaction logging includes:
- `request_id`
- `session_id`
- `event_type`
- routing steps and perf metrics

This enables end-to-end tracing across:
- API request lifecycle
- voice session turns
- tool dispatch and integration calls
