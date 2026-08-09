# Vasya AI App Data

Vasya keeps application code and user-owned runtime data separate. Installers
and GitHub archives must not contain personal projects, tasks, notes, logs,
tokens, databases, downloaded voices, or model caches.

## Platform Profiles

Packaged builds use these roots:

- macOS: `~/Library/Application Support/Vasya AI/`
- Windows: `%APPDATA%/Vasya AI/`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/vasya-ai/`

Each profile contains:

- `config/`: generated `.env` and local integration configuration
- `data/`: SQLite, state files, Memory Center, voices, and project registry
- `logs/`: interaction, voice, and launch-agent logs
- `cache/`: TTS, model, benchmark, and temporary audio caches

`VASYA_APP_DATA_DIR` overrides the profile root for portable development,
testing, or a user-selected location. Individual path environment variables
remain higher-priority overrides.

## Source Checkout Compatibility

A normal source checkout continues to use the repository `.env` and
`storage/` directory. Paths are resolved from the repository root, so launching
Vasya from another working directory does not redirect writes elsewhere.

Set `VASYA_SOURCE_STORAGE_COMPAT=false` in the process environment to exercise
the platform layout from source. Use `VASYA_APP_DATA_DIR` when the destination
must be deterministic.

## Migrating Existing Data

Migration is explicit and copy-only. It never removes the legacy profile and
never overwrites a file already present in the destination. Repeating the same
command is safe and copies only files that are still missing.

```bash
.venv/bin/python scripts/migrate_app_data.py --legacy-root /path/to/old/vasya
```

Use `--app-data-dir /path/to/profile` to select a non-default destination.
Review free disk space first: downloaded voices, TTS engines, models, and caches
can be large. The command reports copied files and existing files it preserved.

After migration, run:

```bash
.venv/bin/python scripts/doctor.py
```

Do not delete the legacy profile until Vasya starts successfully and the
projects, Memory Center, integrations, and voice configuration are present.
