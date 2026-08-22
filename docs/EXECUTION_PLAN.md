# Vasya AI Execution Plan

This is the single ordered work queue for Codex and maintainers. It answers
"what do we implement next?" without duplicating the product strategy or the
technical detail held elsewhere.

## Document Roles

- `ROADMAP.md`: product direction, phases, and release milestones.
- `docs/*_PLAN.md`: architecture, scope, and acceptance details for one track.
- `docs/adr/`: durable decisions and their rationale.
- This file: current status and strict implementation order.

Only this file should identify the next implementation slice. Keep at most one
item `IN PROGRESS`. Update it in the same commit that completes a slice.

## Status Legend

- `DONE`: merged, pushed, and verified by CI.
- `IN PROGRESS`: current local slice; do not start another feature.
- `NEXT`: first eligible slice after the current one.
- `QUEUED`: ordered but not started.
- `BLOCKED`: waiting for an explicit external dependency or decision.

## Current Checkpoint

- Last completed foundation slice: platform app-data paths and copy-only compatibility migration.
- Last completed registry slice: user-owned registry with Control Center CRUD management.
- Last completed backup slice: versioned allowlist export with explicit secret and payload exclusions.
- Current implementation item: backup and restore for non-secret user state.
- Next slice: validate archives and preview import changes without writing state.
- Personal/public data separation is accepted in
  `docs/adr/ADR-003-public-app-and-private-user-data.md`.
- The existing unsigned macOS ZIP is a tester artifact, not a general release.

## Ordered Queue

### 1. DONE: Finish Project OS Voice Navigation

Scope: complete the current read-only commands for project summaries and
dashboard targets.

Acceptance:

- "Что дальше по проектам?" returns a concise local status summary.
- "Открой ai_pal" returns a validated Control Center navigation target.
- HTTP and voice pipeline clients receive the optional navigation target.
- No repository mutation or OS action is triggered.

Verification:

- `.venv/bin/python -m unittest tests.test_project_os_commands`
- Existing orchestrator, voice pipeline, project registry, and API tests.
- Full unit suite, scoped `compileall`, `git diff --check`, push, and green CI.

### 2. DONE: Introduce Platform App-Data Paths

Scope: add one resolver for config, databases, logs, caches, project registry,
and Memory Center data outside the application bundle.

Acceptance:

- Packaged mode never requires a writable launch directory.
- Source-checkout development keeps a documented compatibility path.
- Existing data is preserved through an explicit, idempotent migration.
- Tests cover macOS, Windows, Linux, first run, and existing-data behavior.

Reference: `docs/adr/ADR-003-public-app-and-private-user-data.md`.

### 3. DONE: Add The User Project Registry

Scope: replace source-level personal presets as the normal workflow with a
local user-owned registry and Control Center management UI.

Acceptance:

- Fresh installs contain no maintainer projects.
- A user can add, edit, disable, and remove a local project.
- Paths are validated without scanning the machine or mutating repositories.
- Registry data survives app upgrades and can be exported for backup.

### 4. IN PROGRESS: Add Backup And Restore For User State

Scope: export and restore non-secret settings, project mappings, and local
Vasya records.

Acceptance:

- Secrets and large model/cache files are excluded.
- Import previews changes and never silently overwrites newer data.
- The archive format is versioned and documented.

Reference: `docs/adr/ADR-004-versioned-user-backups.md`.

### 5. QUEUED: Define The Read-Only Connector Contract

Scope: define connector identity, availability, capabilities, permissions,
source provenance, sync cursor, and health status.

Acceptance:

- Connectors declare read and write capabilities separately.
- Unsupported platform capabilities are visible, not treated as failures.
- Project OS can list connector readiness without running a sync.
- External writes cannot bypass the future approval queue.

### 6. QUEUED: Add Eva Via Apple Reminders And Calendar

Scope: implement a macOS read-only EventKit connector for selected Eva-synced
lists and calendars.

Acceptance:

- The connector is opt-in and permission-aware.
- Tasks, task notes, dates, completion state, and events retain source ids.
- Repeated sync is idempotent and records provenance and sync time.
- Windows and Linux report the connector as unavailable.
- No Eva private files are read and no reminders/events are changed.

### 7. QUEUED: Build The Unified Project Read Model

Scope: map Git status, project metadata, imported tasks/events, notes, and
Memory Center context into one project detail projection.

Acceptance:

- Every record shows its source and last synchronization state.
- Duplicate records are not created by repeated connector sync.
- Control Center shows next tasks, blockers, recent context, and source health.

### 8. QUEUED: Complete The Public macOS Release Foundation

Scope: make the existing macOS artifact safe for users outside the repository.

Acceptance:

- First run configures app-data storage and optional integrations.
- Microphone and Accessibility permission guidance is verified.
- A clean-machine smoke passes without Python, a virtualenv, or a repo clone.
- GitHub Release automation produces checksummed artifacts from a tag.

### 9. QUEUED: Sign, Notarize, And Package The macOS Release

Scope: produce the first broadly downloadable macOS release.

Acceptance:

- The app is signed and notarized.
- A DMG or equivalent polished artifact is published.
- Release notes identify external Ollama/model requirements and limitations.
- Upgrade smoke confirms that user data is preserved.

### 10. QUEUED: Add The Agent Action Queue And Approval Inbox

Scope: begin mutating project operations only after the personal-data,
connector, and release foundations are stable.

Acceptance:

- Read-only actions can run immediately.
- Create task, test, commit, push, and connector writes require the appropriate
  confirmation policy.
- Every run records request, plan, approval, command summary, result, and
  artifacts.

## Slice Completion Protocol

For every implementation item:

1. Confirm scope and dependencies from the linked thematic plan or ADR.
2. Add a failing focused test before behavior changes.
3. Implement one complete slice, normally touching no more than five files.
4. Run targeted tests, then the full suite and compile checks.
5. Review the diff for secrets, personal paths, unrelated edits, and user-data
   compatibility.
6. Commit and push the slice independently.
7. Confirm GitHub CI, mark the item `DONE`, and promote the next item.

Do not mark work complete based only on code presence. Completion requires
verification, a pushed commit, and green CI.
