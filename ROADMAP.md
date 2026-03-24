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

Targets:
- menu bar app or lightweight desktop shell
- global hotkey
- floating widget or avatar
- visible states: listening, thinking, speaking, error

Recommended order:
1. hotkey
2. floating widget MVP
3. menu bar app
4. richer avatar and animation
5. compact response bubble and settings

Why this matters:
- a desktop assistant should feel immediately available, not hidden behind terminal commands

## Phase 4: Structured integrations

Focus:
- extend the assistant without breaking the local core

Targets:
- deeper Google Calendar sync
- Obsidian export and note workflows
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
- `v0.4.x`: installation polish, diagnostics, better voice recovery, tray and widget UX
- `v0.5.x`: fuller desktop shell with menu bar or tray integration
- `v0.6.x`: Obsidian integration
- `v0.7.x`: code agent and writing/research agent
- `v0.8+`: richer multi-agent and desktop workflows

## Near-term recommendation

If choosing one practical path from here, the best next order is:

1. Finish the first desktop widget MVP
2. Improve speech understanding and recovery UX
3. Simplify setup and first-run experience
4. Add Obsidian integration
5. Add code and writing agents
