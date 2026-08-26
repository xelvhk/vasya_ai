# ADR-004: Versioned User Backup Archives

## Status

Accepted

## Date

2026-08-22

## Context

Vasya AI keeps user-owned project mappings and runtime state outside the
application bundle. Reinstalling, moving to another computer, and recovering
from a failed upgrade require a portable backup that cannot silently collect
credentials, integration payloads, model files, or unrelated data from the
computer.

A denylist is not sufficient for this boundary. New runtime files could appear
without being classified and would then leak into backups by default. Copying a
live SQLite database or the Memory Center directory also produces unclear
consistency and conflict semantics for restore.

## Decision

### Archive Contract

User backups are ZIP archives with exactly one required root entry,
`manifest.json`, and zero or more allowlisted state entries under `state/`.
The current contract is:

- format id: `vasya-user-backup`;
- archive version: `1`;
- export policy: `portable-json-allowlist-v1`;
- UTF-8 JSON payloads;
- SHA-256 and byte size recorded for every state entry;
- archive file permissions set to `0600` where the platform supports them;
- atomic destination replacement only after every source has passed validation.

The manifest shape is:

```json
{
  "format": "vasya-user-backup",
  "version": 1,
  "created_at": "2026-08-22T08:30:00Z",
  "policy": "portable-json-allowlist-v1",
  "files": [
    {
      "path": "state/project_registry.json",
      "size": 217,
      "sha256": "<64 lowercase hexadecimal characters>"
    }
  ]
}
```

Version `1` may gain new optional allowlisted entries. A change to required
manifest fields, checksum semantics, or restore interpretation requires a new
archive version.

### Export Allowlist

The first exporter includes only existing regular, non-symlink JSON files with
these names:

- `avatar_custom_skin.json`;
- `avatar_widget.json`;
- `child_mode.json`;
- `dictation_mode.json`;
- `morning_show_state.json`;
- `project_registry.json`;
- `tts_settings.json`;
- `user_profile.json`.

Each file must be valid UTF-8 JSON and below the configured size limit. Export
fails before replacing the destination if an allowlisted payload contains a key
classified as a token, password, secret, credential, API key, access key, or
private key. This is defense in depth; sensitive state must not use these files
in the first place.

### Explicit Exclusions

The exporter does not recursively scan the application-data directory. The
following categories are excluded even if they are present:

- `.env`, keyring values, credentials, OAuth tokens, API tokens, and secret
  stores;
- `integrations.json`, `integration_secrets.json`, provider sync state, and raw
  integration payloads;
- SQLite databases, legacy task/calendar stores, Memory Center content, and
  imported notes until logical export and conflict rules exist;
- logs, recordings, generated audio, crash data, and interaction history;
- caches, downloaded models, TTS engines, voices, benchmarks, and temporary
  files;
- unknown files, directories, and symbolic links.

SQLite and Memory Center data may be added later as logical, versioned records.
They must not be added by copying live storage files into the archive.

### Import Preview

Import preview is read-only. It validates the complete archive before comparing
entries with local state and returns one status per declared file:

- `create`: the local state file does not exist;
- `unchanged`: local bytes and archive bytes are identical;
- `conflict`: local state differs, cannot be read, is not a regular file, or is
  a symbolic link.

Preview rejects malformed manifests, unsupported versions or policies,
undeclared and unknown entries, duplicate paths, path traversal, symbolic
links, encrypted entries, expansion beyond size limits, checksum mismatches,
invalid JSON, and secret-like keys. It does not create the target directory or
write any state.

### Restore Safety Contract

Restore reuses the same complete archive validation as preview before it writes
any state. Its contract is:

1. Reject unsupported format ids and future versions.
2. Reject duplicate entries, absolute paths, path traversal, links, and entries
   not declared in the manifest and policy allowlist.
3. Verify every declared byte size and SHA-256 checksum.
4. Parse and validate all JSON payloads before changing local state.
5. Produce a preview describing creates, unchanged entries, conflicts, and
   excluded content.
6. Require explicit confirmation before replacing newer or conflicting data.
7. Apply accepted changes atomically and preserve `0600` permissions.

`restore_user_backup(..., allow_conflicts=False)` is the safe default. It
raises `BackupConflictError` with every conflicting archive path before
creating or replacing any state file. Setting `allow_conflicts=True` permits
replacement only when the local target is a regular readable file whose bytes
differ. Symbolic links, directories, and unreadable targets remain blocked.

Changed payloads are first written to a private staging directory on the same
filesystem. Existing regular files are moved into a rollback directory before
staged files are installed with `os.replace`. If an operational error occurs,
all files already applied by that restore are removed and every original is
put back. This gives the restore batch rollback semantics for handled failures;
each installed file is atomically replaced and receives `0600` permissions.

An archive is private user data. It is never committed to the repository,
attached to diagnostics, or uploaded automatically.

## Consequences

- Fresh and existing installations get a predictable portable export boundary.
- Unknown future runtime files remain excluded by default.
- A malformed or suspicious allowlisted source blocks export instead of
  producing a potentially unsafe archive.
- Version 1 initially protects project mappings and portable UI preferences,
  but it is not yet a complete backup of tasks, notes, or Memory Center data.
- Import preview, explicit conflict confirmation, rollback, and synthetic
  round-trip coverage now complete the version 1 backup/restore slice.
