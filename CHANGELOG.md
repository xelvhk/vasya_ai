# Changelog

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
