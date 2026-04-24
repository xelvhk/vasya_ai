# vasya_ai

Local-first voice AI assistant for desktop productivity.

`vasya_ai` is a product-oriented assistant that helps manage tasks, events, notes, and integrations through voice and text, with local-first storage and optional external sync.

Language: **English** | [Русский](README.ru.md)

## Product Value
- Local-first workflow: core data stays on your machine (SQLite + local files)
- Voice-first UX with fast command loop
- Practical integrations: Google Calendar, Notion, GitHub
- API layer for future web/mobile clients (`FastAPI`)

## Use Cases
- Personal planner: add/list/complete tasks and schedule events by voice
- Daily assistant: morning briefing (weather + quote), reminders, quick notes
- Integration assistant: sync GitHub updates to Notion, export notes to Obsidian
- Automation sandbox: test local agent orchestration and routing policies

## Stack
- Python 3.11+
- FastAPI
- Ollama (local LLM)
- faster-whisper (STT)
- SQLite
- sounddevice + scipy

## Quick Start
```bash
git clone https://github.com/xelvhk/vasya_ai.git
cd vasya_ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/doctor.py
python main.py
```

Optional API mode:
```bash
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8787 --reload
```

## Environment
Copy `.env.example` to `.env` and adjust values for your machine.

Key groups:
- LLM and voice: `OLLAMA_*`, `WHISPER_*`, `VOICE_*`
- UI and hotkeys: `HOTKEY_*`, `AVATAR_*`, `TTS_*`
- Integrations: `GOOGLE_CALENDAR_*`, `NOTION_*`, `GITHUB_*`
- API: `VASYA_API_AUTH_TOKEN`

## Architecture
```text
Input Layer
  voice/recorder.py, voice/stt.py, voice/pipeline.py

Orchestration Layer
  core/orchestrator.py, core/router.py, core/intent_parser.py

Domain Agents
  agents/task_agent.py, agents/calendar_agent.py, agents/note_agent.py, agents/chat_agent.py, agents/game_agent.py

Services + Repositories
  services/* + repositories/*

Storage + Integrations
  storage/vasya.db + external adapters (Google Calendar / Notion / GitHub)

API Layer
  apps/api/* (FastAPI endpoints for chat/tasks/events/notes)
```

## Demo / Screenshots
- Add product screenshots to `docs/screenshots/` (placeholder)
- Suggested assets: `avatar-widget.png`, `voice-flow.png`, `api-docs.png`

## Roadmap
Short roadmap:
- [ ] Stabilize voice quality profiles and recovery flow
- [ ] Add test coverage for critical services and routers
- [ ] Improve onboarding script for zero-friction local setup
- [ ] Prepare API for web/mobile thin clients

Detailed roadmap and release timeline:
- [ROADMAP.md](ROADMAP.md)
- [docs/MOBILE_MONOREPO_PLAN.md](docs/MOBILE_MONOREPO_PLAN.md)

## CI
Minimal CI is configured in `.github/workflows/ci.yml`:
- install dependencies
- run syntax check (`python -m compileall .`)

## License
No license file is included yet. Add `LICENSE` if you plan public reuse.
