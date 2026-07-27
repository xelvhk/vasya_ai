# Changelog

## v0.7.0 - Draft

### Added
- First macOS installable artifact track with a PyInstaller `.app` prototype and unsigned ZIP wrapper.
- `scripts/build_macos_app.py` for local unsigned `.app` builds.
- `scripts/smoke_macos_app.py` for structure and short launch smoke checks.
- `scripts/build_macos_doctor.py` for a packaged doctor companion prototype.
- `scripts/package_macos_app.py` for `Vasya-AI-macos-unsigned.zip` creation with both app and doctor companion payloads.
- `scripts/smoke_macos_zip.py` for top-level ZIP payload validation.
- Build-only packaging dependency pin in `requirements-build.txt`.
- Packaging prototype and release checklist docs for the `v0.7.0` artifact path.

### Changed
- Promoted the packaging roadmap from discovery to a repeatable local artifact flow.

### Verification
- Expected release checks: unit test suite, scoped source `compileall`, strict doctor smoke, packaging smoke, unsigned ZIP creation, and GitHub Actions CI.

### Known Limitations
- The first macOS artifact is unsigned and not notarized.
- Ollama, microphone permission, Accessibility permission, and optional integration credentials remain external prerequisites.
- The doctor companion is a separate top-level folder inside the ZIP, not yet an in-app diagnostics flow.
- DMG/signing automation remains follow-up work.

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
