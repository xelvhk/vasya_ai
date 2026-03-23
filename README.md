# Vasya AI

`VAS = Voice AI Assistant`

Language: **English** | [Русский](README.ru.md)

Local-first voice AI assistant with a current macOS MVP and a longer-term path toward Windows and Linux.
Vasya is evolving from a CLI MVP into a broader desktop personal AI system with tasks, calendar, future note workflows, and specialized agents.

Current version: `0.4.0`

## Overview

Vasya already supports:
- local voice input
- local speech-to-text
- intent parsing through a local LLM via Ollama
- task management
- calendar event creation and listing
- Google Calendar event sync and import
- local SQLite storage
- macOS speech output through `say`
- background hotkey voice activation
- first floating desktop avatar widget MVP

Roadmap:
- see [ROADMAP.md](ROADMAP.md)

## Current MVP

Current capabilities:
- record audio from the microphone
- transcribe speech locally
- route commands to tasks and calendar flows
- parse common Russian date and time phrases
- create, list, complete, and delete tasks
- create, list, and delete events
- filter tasks and events by date
- keep local data in SQLite
- optionally sync calendar events with Google Calendar
- run in background and start voice capture by hotkey
- show a floating avatar widget with click-to-talk states

Example commands:
- `Add a task to buy a lamp`
- `What tasks do I have?`
- `Add a meeting with Sasha tomorrow at 6 PM`
- `Show my events for March 30`

## Stack

- Python
- Ollama
- Llama 3
- faster-whisper
- sounddevice
- scipy
- pydantic
- SQLite

## Architecture

Current pipeline:

`Voice -> audio recording -> Whisper STT -> text -> Ollama -> intent parsing -> router -> agent -> local action -> response`

Storage model:
- tasks and events are stored in `storage/vasya.db`
- legacy JSON files are kept only as migration input
- integrations are treated as adapters on top of the local core

## Project Structure

```text
ai_pal/
├── main.py
├── test_text.py
├── requirements.txt
├── .env
├── README.md
├── README.ru.md
├── ROADMAP.md
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── prompts.py
│
├── core/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── intent_parser.py
│   ├── router.py
│   └── models.py
│
├── agents/
│   ├── __init__.py
│   ├── calendar_agent.py
│   └── task_agent.py
│
├── assistant/
│   ├── __init__.py
│   └── state.py
│
├── scripts/
│   ├── avatar_widget.py
│   ├── doctor.py
│   ├── hotkey_daemon.py
│   └── setup_mac.sh
│
├── services/
│   ├── __init__.py
│   ├── ollama_client.py
│   ├── google_calendar_client.py
│   ├── calendar_service.py
│   └── task_service.py
│
├── repositories/
│   ├── __init__.py
│   ├── event_repository.py
│   └── task_repository.py
│
├── storage/
│   ├── db.py
│   └── .gitkeep
│
├── voice/
│   ├── __init__.py
│   ├── recorder.py
│   ├── stt.py
│   └── tts.py
│
└── utils/
    ├── __init__.py
    ├── datetime_parser.py
    ├── humanize.py
    ├── json_utils.py
    └── logger.py
```

## Run

Fast macOS setup:

```bash
bash scripts/setup_mac.sh
```

Environment diagnostics:

```bash
python scripts/doctor.py
```

1. Clone the repository

```bash
git clone <repo_url>
cd ai_pal
```

2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Install Ollama and download a model

```bash
brew install ollama
ollama run llama3
```

If Ollama is already installed and the model is available locally, that is enough.
On startup, `main.py` also tries to launch `ollama serve` automatically.

5. Run the project

Text-based test:

```bash
python test_text.py
```

Voice workflow:

```bash
python main.py
```

Background hotkey mode:

```bash
python scripts/hotkey_daemon.py
```

Desktop avatar widget MVP:

```bash
python scripts/avatar_widget.py
```

Notes:
- left click starts one voice interaction
- drag moves the avatar on screen
- set `AVATAR_IMAGE_PATH` to use your own PNG avatar
- widget position is restored between launches
- response bubble is shown next to the avatar during listening, thinking, speaking, and errors
- right click closes the widget

Current platform focus:
- the working MVP is currently oriented around macOS
- future roadmap includes Windows and Linux support

## Configuration

Main settings live in `config/settings.py`.

Example values:

```env
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3
AUDIO_FILENAME=input.wav
RECORD_SECONDS=5
WHISPER_MODEL=base

TTS_VOICE=Milena
TTS_RATE=185
TTS_BACKEND=auto
VOICE_INPUT_BACKEND=auto
HOTKEY_COMBINATION=<ctrl>+<alt>+space
HOTKEY_EXIT_COMBINATION=<ctrl>+<alt>+q
AVATAR_IMAGE_PATH=
AVATAR_SIZE=140
AVATAR_STATE_FILE=storage/avatar_widget.json

STORAGE_DB_FILE=storage/vasya.db
CALENDAR_STORAGE_FILE=storage/calendar.json
TASK_STORAGE_FILE=storage/tasks.json

GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=storage/google_token.json
GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_TIMEZONE=Europe/Moscow
GOOGLE_CALENDAR_DEFAULT_EVENT_DURATION_MINUTES=60
GOOGLE_CALENDAR_SYNC_ON_READ=true
GOOGLE_CALENDAR_READ_MAX_RESULTS=20
```

Voice selection:

```bash
python -m voice.tts --list-voices
python -m voice.tts --voice Milena --text "Hello, this is a voice test"
```

## Google Calendar

Setup:
1. Create a Desktop App OAuth client in Google Cloud
2. Enable Google Calendar API
3. Save the credentials file as `credentials.json` in the project root
4. Enable the integration in `.env`

Behavior:
- new events can be pushed to Google Calendar
- upcoming Google Calendar events can be imported into SQLite
- if Google sync fails, Vasya keeps working with local storage and reports the error

## Current Limitations

This is still an MVP, so current limits include:
- no wake word yet
- no always-listening mode
- speech understanding still needs improvement in noisy or imperfect conditions
- the desktop avatar is still a first lightweight widget, not a full desktop app
- no menu bar app yet
- no Obsidian integration yet
- no long-term memory yet
- no specialized code or writing agents yet

## Version Path

- `v0.3.x`: core voice MVP, local storage, calendar/tasks, Google Calendar, hotkey mode
- `v0.4.0`: first desktop widget MVP with assistant state layer and click-to-talk avatar
- `v0.4.x`: installation polish, voice understanding improvements, better desktop UX
- `v0.5.x`: fuller desktop shell with tray or menu bar app and richer avatar behavior
- `v0.6.x`: Obsidian integration
- `v0.7.x`: code agent and writing/research agent

## Planned Direction

Near-term goals:
- better phrase understanding and retry UX
- simpler installation and onboarding
- better desktop shell around the current widget MVP
- Obsidian integration
- specialized code and writing agents

Full long-term plan:
- see [ROADMAP.md](ROADMAP.md)

## Security

When using external integrations, the main concerns are:
- token storage
- calendar access
- file access
- action logging

## Notes

On macOS, microphone access may be required for Terminal or your IDE:
- `System Settings`
- `Privacy & Security`
- `Microphone`

Global hotkeys on macOS may also require:
- `System Settings`
- `Privacy & Security`
- `Accessibility`

Running the desktop avatar may also require:
- `System Settings`
- `Privacy & Security`
- `Accessibility`

## Author

Xelvhk

Personal project for building a local voice AI assistant that can grow into a wider personal AI system.
