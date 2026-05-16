# Vasya AI Roadmap

This roadmap is intentionally pragmatic.
The goal is to grow Vasya from a local voice MVP into a usable desktop AI system without overengineering the early stages.

## Product direction

The long-term target is a desktop AI assistant that:
- lives as a lightweight desktop presence
- can be triggered by a hotkey or avatar click
- supports voice-first interaction
- manages tasks, calendar, notes, and personal workflows
- can grow through specialized agents such as coding and research/writing agents
- remains local-first where practical
- can later support macOS, Windows, and Linux

## Guiding principles

- Keep the core architecture simple and modular
- Prefer stable local workflows before adding new integrations
- Add external services as adapters, not as the system core
- Reduce setup friction over time until the app feels close to one-click install
- Improve recognition and feedback loops before adding more UI polish

## Phase 1: Stabilize the core assistant

Focus:
- improve speech recognition quality and command understanding
- make task and calendar UX more natural
- reduce ambiguity and add confirmation flows
- improve logging and diagnostics

Targets:
- better retry flow when speech is transcribed poorly
- more natural task and event responses
- stronger support for date phrases like `today`, `tomorrow`, `this week`
- clearer error messages for integrations and local failures

Why this matters:
- if voice understanding is unreliable, every later feature feels broken

## Phase 2: Installation and onboarding

Focus:
- make setup dramatically easier

Targets:
- setup automation with a macOS-first MVP path
- environment and dependency validation
- first-run setup flow
- model and integration checks

Likely deliverables:
- `setup_mac.sh`
- `doctor` command or diagnostics script
- guided `.env` creation

Later:
- Windows setup path
- Linux setup path

Why this matters:
- setup friction is one of the biggest barriers to real usage

## Phase 3: Desktop shell

Focus:
- move from script-style usage to real desktop presence

Current status:
- background hotkey mode is already implemented
- first floating avatar widget MVP is available as `v0.4.0`
- tray-controlled desktop shell groundwork is in progress in `v0.4.x`
- conversational UX, confirmations, and faster chat flow are now in `v0.4.1`
- child game mode and a dedicated game agent are now in `v0.4.2`
- notes memory and Obsidian export landed in `v0.4.3`
- voice responsiveness and child-safe/game UX improved in `v0.4.4`
- two-stage STT, STT quality profiles, smarter recovery, and better clarifications landed in `v0.4.5`
- avatar personalization, built-in skins, custom palette import/export, custom avatar images, and child-mode auto skin switching landed in `v0.4.6`
- first-run onboarding dialog and checklist/progress polish landed in `v0.4.7`
- product shell hover tooltip and status indicator landed in `v0.5.0`
- mini hover tooltips per state landed in `v0.5.1`
- tool registry, routing policy layer, and handoff rules landed in `v0.5.2`
- managed user profile memory, fast-path memory commands, and settings cleanup landed in `v0.5.3`
- Notion adapter MVP with GitHub update sync landed in `v0.5.4`
- conversational speed profile (quick chat + shorter follow-up delay) landed in `v0.5.5`
- voice latency instrumentation and speed report tooling landed in `v0.5.6`
- hotkey-based text command window for precise command input landed in `v0.5.7`
- voice-open text command window, first daily morning show, and faster local fast-lane routing landed in `v0.5.8`
- A/B voice contour metrics, adaptive auto-interrupt thresholds, and hover/tray health hints landed in `v0.5.9`
- API gateway foundation for future mobile/web clients landed in `v0.5.10`
- voice dictation to active focused field (Obsidian-first MVP) landed in `v0.5.19`
- continuous dictation mode with start/stop commands, punctuation helpers, focus-safe guardrails, and optional API target landed in `v0.5.20`
- security hardening baseline (API auth strict mode, secrets storage via keyring, log redaction, safer dictation API host policy) landed in `v0.5.21`
- API/WS rate-limit layer for anti-abuse protection landed in `v0.5.22`
- security test baseline (e2e auth/throttling/log redaction) landed in `v0.5.23`
- managed Obsidian vault bootstrap (folders/templates/frontmatter+links index/recommended plugin manifest) landed in `v0.5.24`
- Memory Center foundation landed in `v0.5.25`: local memory sources/chunks, Markdown artifacts, sync-state tracking, and `/v1/memory/status`
- GitHub/Notion/Obsidian Memory Center sync landed in `v0.5.26` with `/v1/memory/sync`
- Desktop shell Memory Center controls landed in `v0.5.27`: status view and manual sync from the avatar/tray menu
- Background Memory Center sync landed in `v0.5.28` with a desktop-process scheduler
- Memory Center search landed in `v0.5.29` with local provenance-backed retrieval
- Desktop Memory Center search landed in `v0.5.30` through avatar/tray menu actions
- Voice/text Memory Center commands landed in `v0.5.31` for status, sync, and search
- Memory Center recent view landed in `v0.5.32` for latest chunks and "what's new" commands
- Desktop Memory Center recent view landed in `v0.5.33` through avatar/tray menu actions
- Memory Center daily digest landed in `v0.5.34` with local Markdown artifacts and `/v1/memory/digest`
- Desktop Memory Center daily digest action landed in `v0.5.35` through the avatar/tray menu
- Memory Center digest history landed in `v0.5.36` with `/v1/memory/digests`, desktop action, and fast command

Targets:
- menu bar app or lightweight desktop shell
- global hotkey
- floating widget or avatar
- visible states: listening, thinking, speaking, error
- alternate avatar skins and character presentation presets
- user-imported palette themes and optional image-based avatar overrides

Recommended order:
1. hotkey
2. floating widget MVP
3. menu bar app
4. richer avatar and animation
5. compact response bubble and settings
6. skin system and avatar personalization

Why this matters:
- a desktop assistant should feel immediately available, not hidden behind terminal commands

## Phase 4: Structured integrations

Focus:
- extend the assistant without breaking the local core

Targets:
- deeper Google Calendar sync
- deeper Obsidian workflows beyond export
- Notion adapter for workspace-style use
- optional integrations with tools like Todoist or Google Tasks

Recommended architecture:
- keep SQLite as local state
- treat integrations as adapters with `source` and `external_id`

Why this matters:
- this keeps the system coherent and avoids coupling Vasya to one external product

## Phase 5: Agent system

Focus:
- support specialized assistants without turning the codebase into a framework mess

Core idea:
- one orchestrator
- multiple task-specific agents
- clear contracts for inputs, outputs, and tools

Near-term candidates:
- `code_agent`
- `writing_agent`
- `obsidian_agent`
- richer `calendar_agent`

Why this matters:
- the project can grow by adding capabilities instead of rewriting the core

## Priority agents

### Code agent

Should help with:
- reading local codebases
- editing files
- running commands
- writing features, fixes, tests, and docs

### Writing and research agent

Should help with:
- drafting scientific articles
- outlining arguments
- rewriting academic text
- organizing notes for future export to Obsidian

## Obsidian direction

Obsidian should be treated as:
- note memory
- research workspace
- daily log and knowledge base

Not as:
- the main operational database for the assistant

Good future exports:
- meeting notes
- research notes
- daily summaries
- inbox items
- task and project notes

## Suggested version path

- `v0.3.x`: voice reliability, task/calendar UX, better phrasing
- `v0.4.0`: assistant state layer and first floating desktop avatar widget
- `v0.4.1`: conversational UX improvements, confirmation flows, faster chat path
- `v0.4.2`: child game mode and dedicated game agent
- `v0.4.3`: local notes memory and Obsidian export
- `v0.4.4`: voice responsiveness, child-safe UX, and game interaction polish
- `v0.4.5`: two-stage STT, STT quality profiles, smarter recovery, and clearer task/calendar clarifications
- `v0.4.6`: avatar personalization, built-in skins, custom palette import/export, custom avatar image overrides, and child-mode auto skin switching
- `v0.4.7`: first-run onboarding dialog, checklist, and polish
- `v0.5.0`: hover tooltip, status indicator, and more product-like desktop shell polish
- `v0.5.1`: mini hover tooltips per state
- `v0.5.2`: tool registry, routing policy layer, handoff rules, and unified local memory API
- `v0.5.3`: managed user profile memory, faster memory command routing, and settings-based personal memory cleanup
- `v0.5.4`: Notion read/write adapter, GitHub-to-Notion project sync, and fast Notion voice intents
- `v0.5.5`: conversational speed profile with quick chat prompt/model routing and reduced follow-up latency
- `v0.5.6`: voice performance metrics, speed report command, and ultra-fast voice mode tuning
- `v0.5.7`: desktop text command window via hotkey with router integration for Notion/GitHub flows
- `v0.5.8`: voice command for text input window, morning show (weather + quote), and faster local fast-lane routing
- `v0.5.9`: A/B voice contour metrics, adaptive auto-interrupt thresholds, and shell health hints in hover/tray
- `v0.5.10`: API gateway foundation (`apps/api`) for future iOS/Android clients over shared core logic
- `v0.5.11`: context/action layer (selected text context, screenshot-aware prompts, and slash-style quick actions)
- `v0.5.12`: OS action tools with allowlist/confirmation safety, plus role-spec routing and prompt packs for agent behavior
- `v0.5.13`: A/B voice metrics for routing/prompt profiles, role mix visibility, and TTFR/TTA comparison by profile
- `v0.5.14`: optional XTTS backend and hybrid speech mode for better naturalness without losing short-reply speed
- `v0.5.15`: runtime prewarm for STT/Ollama plus more aggressive early fast-path for low-risk intents
- `v0.5.16`: voice-first Obsidian note updates and GitHub README -> Obsidian project sync
- `v0.5.17`: pre-generated morning show cache and fast weather small-talk replies
- `v0.5.18`: streaming/pipeline orchestration, WebSocket realtime mode, modular STT/TTS/LLM registry, and benchmark harness
- `v0.5.19`: voice dictation to active focused field (`os_type_text`), including fast RU phrasings like "добавь текст..." and "продиктуй..."
- `v0.5.25`: Memory Center foundation with provenance-backed local chunks, wiki artifacts, sync cursors, and status API
- `v0.5.26`: source sync into Memory Center for GitHub commits/PRs, Notion page snapshots, and Obsidian vault notes
- `v0.5.27`: desktop Memory Center surface with status summary and sync-now action
- `v0.5.28`: background Memory Center scheduler for periodic non-forced source refresh
- `v0.5.29`: Memory Center search endpoint over local chunks and Markdown artifacts
- `v0.5.30`: desktop Memory Center search action with snippets and provenance paths
- `v0.5.31`: fast voice/text intents for Memory Center status, sync, and search
- `v0.5.32`: recent Memory Center endpoint and voice/text "what's new in memory" command
- `v0.5.33`: desktop Memory Center recent action for latest chunks
- `v0.5.34`: deterministic Memory Center daily digest endpoint and voice/text command
- `v0.5.35`: desktop Memory Center daily digest action
- `v0.5.36`: Memory Center digest history endpoint, desktop action, and voice/text command
- `v0.5.20`: continuous dictation mode (start/stop), punctuation helpers, focus-safe typing guardrails, and optional API text target
- `v0.5.21`: security hardening baseline (strict API auth defaults, keyring-backed integration secrets, log redaction controls, safer dictation API host allowlist)
- `v0.5.22`: API/WS throttling layer (HTTP route limits, WS session/message limits) with anti-abuse logs
- `v0.5.23`: security test baseline (`SEC-007`) with e2e coverage for auth/throttling and real log-redaction writes
- `v0.5.24`: managed Obsidian vault bootstrap (knowledge folder model, templates, metadata/link indexing, plugin-manifest helper)
- `v0.5.x`: fuller desktop shell, richer avatar behavior, and user-imported visual themes
- `v0.6.x`: easier installation, starting with Windows, then Linux
- `v0.7.x`: deeper Obsidian workflow and Notion adapter
- `v0.8.x`: code agent and writing/research agent
- `v1.0`: cross-platform Vasya with simple installation, skins, Obsidian + Notion, stable voice UX, and multi-agent workflows

## Near-term recommendation

If choosing one practical path from here, the best next order is:

1. Make the desktop shell feel more product-like
2. Deepen avatar personalization and user theme import
3. Continue improving speech understanding and recovery UX
4. Add context-aware actions (selected text, screenshot prompts, quick slash actions)
5. Simplify setup and first-run experience, starting with Windows setup
6. Deepen adapters such as Obsidian and later Notion

## Security hardening tracker (v0.5.21)

- [x] API: secure-by-default auth mode (`VASYA_API_REQUIRE_AUTH=true`)
- [x] API: reject unconfigured auth token in protected mode
- [x] WebSocket: query-token auth disabled by default
- [x] Integrations: move sensitive tokens to OS keyring (with local fallback)
- [x] Logging: redact secrets and optionally hide free-text payloads
- [x] Dictation API: enforce host allowlist (`DICTATION_API_ALLOWED_HOSTS`)
- [x] Add rate-limit/throttling for `/v1/chat`, `/v1/pipeline`, `/v1/ws/voice`
- [x] Add security-focused tests for auth, logging redaction, and secret migration

## What 1.0 Means

For Vasya, `1.0` should mean:
- macOS, Windows, and Linux support at a practical level
- installation that feels close to download-and-run
- a polished desktop shell with character presence
- stable and fast voice-first UX
- alternate Vasya skins and personalization
- user-imported themes or images for character customization
- local-first core remains the source of truth
- Obsidian and Notion available as adapters and external views
- multiple specialized agents for different workflows
