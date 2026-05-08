# ADR-001: Layering and Dependency Rules

- Status: Accepted
- Date: 2026-05-06
- Decision owner: Vasya AI core

## Context

Vasya AI grew from a single-flow local assistant into a modular system:
- voice pipeline (STT/TTS/session)
- orchestrator/router/tool dispatch
- domain agents and services
- local storage + external adapters
- desktop shell + API gateway

Without explicit dependency boundaries, changes in one area can break unrelated flows and slow down iteration.

## Decision

We use a layered architecture with strict inward dependencies.

Primary layers:
1. Interfaces (contracts/ports): stable abstractions for domain capabilities.
2. Core orchestration: intent parsing, routing, handoffs, tool dispatch.
3. Domain agents/services: task/calendar/notes/games/memory/business flows.
4. Adapters/infrastructure: DB repositories, external APIs, OS actions, TTS/STT backends.
5. Entry points: desktop widget, voice loop, HTTP/WS API.

Dependency rules:
- Entry points can depend on all lower layers.
- Core can depend on interfaces and core models, but not on concrete infra details.
- Domain services depend on interfaces and shared utilities, not on entry points.
- Adapters implement interfaces and are wired at composition boundaries.
- No reverse dependency from core/domain into UI or transport-specific modules.

## Rationale

- Keeps orchestration stable while swapping adapters (e.g., STT/TTS/Notion/Obsidian).
- Reduces regression blast radius.
- Makes tests cheaper: core logic can be tested with fakes.
- Supports multi-client future (desktop + mobile/web API) over same core.

## Consequences

Positive:
- Clear ownership of changes.
- Easier test strategy by layer.
- Better long-term maintainability and onboarding.

Trade-offs:
- Slightly more boilerplate (ports/adapters wiring).
- Requires discipline to avoid convenience cross-imports.

## Enforcement Checklist

- New feature touches only one primary layer plus explicit composition wiring.
- Shared models live in stable modules, not UI scripts.
- External SDK usage stays in adapter/service boundary, not in core router/orchestrator.
- New integration starts with interface contract before implementation.
