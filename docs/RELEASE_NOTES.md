# Release Notes

## v0.6.0 (2026-06-19)
- Promoted Vasya AI to the `0.6.0` Installation & First-Run milestone.
- Added Morning Brief v1: weather, open tasks, today/tomorrow calendar events, Memory Center context, suggested priorities, short spoken summary, and deterministic local Markdown briefings.
- Added an idempotent macOS setup path through `scripts/setup_macos.py`, with `scripts/setup_mac.sh` kept as the stable entrypoint.
- Added `docs/FIRST_RUN.md` and README/README.ru quickstart instructions for a fast local install and first response.
- Expanded doctor diagnostics to cover Python version, virtualenv, dependencies, Ollama, TTS backend readiness, writable storage, Memory wiki path, API auth, Google Calendar readiness, and macOS autostart.
- Upgraded CI from syntax-only checks to a meaningful quality gate: scoped `compileall`, unit tests, and `scripts/doctor.py --strict --quiet`.
- Kept local-first security posture: generated API tokens stay in local `.env`, existing local configuration is preserved, and API auth/rate limits remain enabled by default.
- Release checks: unit test suite, scoped source `compileall`, doctor strict smoke, and GitHub Actions CI should pass before tagging.

## v0.5.50 (2026-06-04)
- Promoted Vasya AI to the official `0.5.50` release line.
- Added Memory Center quick-open actions for desktop search results, allowing matched local Markdown files and source URLs to open directly from tray/search flows.
- Consolidated the Memory Center release arc through local sources/chunks, sync state, search, recent view, daily digest artifacts, digest history, latest digest lookup, and desktop tray actions.
- Kept local-first defaults: SQLite/local files remain the source of truth, with optional GitHub, Notion, Obsidian, and Google Calendar adapters.
- Confirmed secure-by-default API posture: `/v1/*` auth remains required by default, HTTP/WS throttling is enabled, and integration tokens use keyring-backed storage when available.
- Release checks: scoped source `compileall` and the unit test suite should pass before tagging.

## v0.1.0 (Draft)
- Stabilized local voice pipeline (STT -> intent -> tool dispatch -> TTS)
- Added production-oriented desktop shell baseline (avatar/tray/hotkey)
- Added task and calendar core workflows with local-first storage
- Added API security baseline (auth + throttling)
- Added Obsidian/Notion adapter baseline for external knowledge workflows
- Added Memory Center foundation: local memory sources/chunks, Markdown artifacts, sync-state tracking, and `/v1/memory/status`
- Added Memory Center source sync for GitHub, Notion, and Obsidian through `/v1/memory/sync`
- Added desktop Memory Center controls in the avatar/tray menu.
- Added background Memory Center sync scheduler for periodic source refresh.
- Added Memory Center search with snippets and provenance paths.
- Added desktop Memory Center search from the avatar/tray menu.
- Added fast voice/text commands for Memory Center status, sync, and search.
- Added recent Memory Center view for latest chunks and "what's new" commands.
- Added desktop recent Memory Center view from the avatar/tray menu.
- Added deterministic Memory Center daily digest artifacts through `/v1/memory/digest` and fast voice/text commands.
- Added desktop Memory Center daily digest action from the avatar/tray menu.
- Added Memory Center digest history via `/v1/memory/digests`, desktop menu action, and fast voice/text command.
- Added desktop action to open the latest Memory digest file directly from the tray menu.
- Added date-range filtering for digest history through `/v1/memory/digests?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`.
- Added digest history presets through `/v1/memory/digests?range=7d|30d` for quick period queries.
- Added digest history day presets through `/v1/memory/digests?range=today|yesterday`.
- Added `/v1/memory/digests/latest` for a direct latest-digest lookup with the same range/date filters.
- Added fast voice/text command for latest Memory digest lookup.
- Added fast voice/text digest-history commands for week/month ranges.
- Added desktop quick actions for digest history presets: 7 days and 30 days.
- Expanded fast digest-history phrases for natural week/month and 7/30-day wording.
- Added fast digest-history voice phrases for today and yesterday.
- Added desktop quick actions for digest history presets: today and yesterday.
- Added desktop quick actions to open digest files for today and yesterday.
- Simplified tray digest menu by removing overlapping day/week/month duplicate actions.
- Replaced separate digest build/open tray actions with one-click "latest digest" action that auto-builds today digest when no file exists.
- Polished Memory search popup formatting with compact source+title rows and shortened snippets for faster scanning.
- Added doctor diagnostics baseline with structured `OK/WARN/FAIL` checks, actionable fix hints, and API auth + memory path validation.
- Added Memory search quick-open tray actions to open matched local files and source URLs directly after search.
- Added doctor CLI flags `--json`, `--strict`, and `--quiet` for machine-readable output, stricter CI gating, and concise terminal runs.

## v0.5.10
- API gateway foundation added for future web/mobile clients (`apps/api`)
- Faster conversational loop and quick chat profile
- Voice latency metrics and speed report command
- Notion/GitHub sync improvements

## v0.5.x Documentation Refresh (April 24, 2026)
- Product-oriented README structure
- Added `.env.example`
- Added CI workflow (`python -m compileall .`)
- Added screenshots section with project previews
- Added MIT `LICENSE`
- Added `CONTRIBUTING.md`
