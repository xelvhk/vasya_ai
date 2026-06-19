# Changelog

## v0.6.0 - 2026-06-19

### Added
- Morning Brief v1 with weather, tasks, calendar events, Memory Center context, spoken summary, and local Markdown artifacts.
- Idempotent macOS first-run setup through `scripts/setup_macos.py` and the `scripts/setup_mac.sh` wrapper.
- First-run checklist documentation in `docs/FIRST_RUN.md`.
- Expanded doctor diagnostics for Python version, virtualenv/dependencies, Ollama, TTS backend readiness, writable storage, Memory wiki path, API auth, optional integrations, and autostart.

### Changed
- Upgraded CI quality gates to run scoped source `compileall`, the unit test suite, and `scripts/doctor.py --strict --quiet`.
- Updated README and README.ru quickstart paths for the 5-minute local setup flow.
- Set the default application version to `0.6.0`.

### Security
- Preserved secure-by-default API auth and throttling for `/v1/*` and realtime voice paths.
- Kept setup local-first: generated API auth tokens are written only to the local `.env`, and existing `.env` files are not overwritten.

### Verification
- Release checks: `.venv/bin/python -m unittest discover tests`, scoped source `compileall`, `scripts/doctor.py --strict --quiet`, and GitHub Actions CI.

## v0.5.50 - 2026-06-04

### Added
- Memory Center quick-open actions for desktop search results.
- Direct opening of matched local files and source URLs from Memory Center tray/search flows.
- Consolidated release documentation for the Memory Center search/digest/recent stack.

### Changed
- Set the default application version to `0.5.50`.
- Updated README, README.ru, and release notes to reflect the official v0.5.50 release.

### Security
- Kept secure-by-default API posture: `/v1/*` auth remains required by default.
- Retained HTTP/WS throttling and keyring-backed integration token storage.

### Verification
- Expected release checks: scoped source `compileall` and `.venv/bin/python -m unittest discover tests`.
