# ADR-003: Separate The Public App From Private User Data

## Status

Accepted

## Date

2026-08-06

## Context

Vasya AI is both a personal desktop assistant for its maintainer and a product
distributed through GitHub as source code and installable artifacts. Vasya
Project OS also needs to combine project status, tasks, calendars, notes,
Memory Center context, and agent runs without forcing users to copy everything
into another task manager.

The current repository already excludes most local storage and secrets, and a
fresh installation receives an empty project registry. However, several runtime
paths still default to repository-relative files under `storage/`. Personal
project presets also live in source code, even though they are opt-in.

Eva Calendar is used by the maintainer for tasks and notes. Eva exposes its
tasks and events through Apple Reminders and Apple Calendar synchronization;
there is no public Eva API in the currently documented product surface.

## Decision

### Distribution Boundary

GitHub source and release artifacts contain:

- application code, migrations, generic UI assets, tests, and build scripts;
- empty defaults and example configuration without credentials;
- connector contracts and setup instructions;
- no personal projects, tasks, notes, histories, tokens, caches, or local
  models.

User-owned data lives outside the application bundle in a platform-native
application-data directory:

- macOS: `~/Library/Application Support/Vasya AI/`;
- Windows: `%APPDATA%/Vasya AI/`;
- Linux: `~/.local/share/vasya-ai/`.

All access to writable runtime data will move behind one app-data path
resolver. Packaged installs must not depend on the launch working directory.
Secrets remain in the OS keyring where possible.

### Source Ownership

Vasya Project OS is an aggregation and action layer, not the sole source of
truth:

- Git and GitHub own repository state;
- the local Vasya registry owns project identity and connector settings;
- Eva or Apple Reminders owns personal tasks;
- Eva or Apple Calendar owns calendar events;
- Obsidian or explicitly selected local files own durable project notes;
- Memory Center owns normalized searchable snapshots and provenance;
- Vasya owns approval records, agent runs, and dashboard projections.

Imported records retain source id, source type, project mapping, sync time, and
read-only or mutable capability. Read-only ingestion is implemented before
two-way writes.

### Eva Integration

The first Eva integration uses Apple system surfaces instead of reading Eva's
private application database:

1. Eva synchronizes selected tasks to Apple Reminders and events to Apple
   Calendar.
2. A macOS connector reads selected lists and calendars through EventKit.
3. Memory Center indexes normalized read-only records with source provenance.
4. Writes and completion sync remain disabled until the approval and conflict
   model is implemented.
5. Eva backup import may be explored later for data that is not exposed through
   Reminders or Calendar.

Other platforms report the Eva connector as unavailable while keeping the same
connector contract. Cross-platform users can choose another supported task or
calendar source.

## Alternatives Considered

### Keep personal defaults in source code

Rejected because it leaks maintainer-specific product assumptions into every
installation and makes public releases harder to reason about.

### Make Vasya the primary task and notes database

Rejected because it creates duplicate entry, synchronization conflicts, and
unnecessary migration pressure. Vasya should present one operating picture over
tools the user already trusts.

### Read Eva's private on-device database

Rejected because the format is undocumented, fragile across Eva updates, and
inappropriate for a distributable integration.

### Add two-way connector writes immediately

Rejected because conflicts, permissions, deletion semantics, and auditability
must be designed before external data is changed.

## Consequences

- A fresh public installation remains empty and safe.
- Personal configuration can be backed up separately from the application.
- Reinstalling or upgrading the app does not overwrite user data.
- Project OS needs a connector capability model and provenance-aware read
  model.
- Existing relative runtime paths require a focused migration before a polished
  public installer.
- Eva support is macOS/iOS-specific at first, while the connector boundary
  remains cross-platform.
