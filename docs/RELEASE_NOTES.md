# Release Notes

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
