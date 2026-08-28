# ADR-005: Project Connector Contract

## Status

Accepted

## Date

2026-08-26

## Context

Vasya Project OS needs to aggregate project state from local repositories,
GitHub, Codex, Obsidian, Apple Reminders and Calendar, and later providers
without coupling the dashboard to provider SDKs. Connectors also need to report
that a platform, setup step, or permission is unavailable without treating that
normal state as an operational failure.

Read-only ingestion comes before external writes. A connector boundary must not
create a second path around the future action queue and approval inbox.

## Decision

### Descriptor And Capability Model

Every connector exposes an immutable `ConnectorDescriptor` containing a stable
lowercase id, display name, and explicit capabilities. Each capability declares:

- a stable operation id such as `tasks.read`;
- access as `read` or `mutating`;
- execution as `direct` or `approval_queue`.

A mutating capability is invalid unless its execution policy is
`approval_queue`. The current `ProjectConnector` protocol intentionally has
no direct mutation method.

### Readiness

`inspect_readiness()` returns availability, setup, permission, health, and an
optional user-facing detail. It must be lightweight and side-effect free: it
does not request permissions, authenticate, synchronize, or read provider
records.

`ProjectConnectorRegistry` lists descriptors and readiness in stable connector
id order. Unsupported platforms are represented as `unavailable`, not raised
as failures. An unexpected readiness exception becomes a generic `degraded`
status without exposing provider exception text.

### Read Contract And Provenance

`read(cursor)` returns a `ConnectorReadBatch` containing normalized records
and an optional next cursor. Every record retains:

- connector id;
- provider source type and source id;
- optional Vasya project id;
- timezone-aware synchronization time;
- normalized provider payload.

A batch rejects records or cursors belonging to another connector. Provider
responses remain untrusted input; each concrete adapter validates and
normalizes them before constructing contract records.

## Consequences

- The dashboard can list connector identity, capabilities, and readiness without
  running synchronization.
- Eva can report EventKit as unavailable on Windows and Linux through the same
  contract used on macOS.
- Repeated reads can retain provider cursors and source provenance.
- External writes remain blocked until the action queue exists.
- The Eva descriptor and platform availability adapter now exist, but the
  connector does not yet request EventKit permission, read records, persist
  cursor state, expose an API route, or add connector UI.
