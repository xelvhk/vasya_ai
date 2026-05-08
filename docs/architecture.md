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

## API surface

Main API module: `apps/api/main.py`

Key routes:
- system: `/health`, `/health/live`, `/health/ready`
- chat/pipeline: `/v1/chat`, `/v1/pipeline`
- realtime: `/v1/ws/voice`
- tasks/notes/events/recovery

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
