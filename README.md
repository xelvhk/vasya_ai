# Vasya AI

`VAS = Voice AI Assistant`

Language: **English** | [Русский](README.ru.md)

Local-first voice AI assistant with a current macOS MVP and a longer-term path toward Windows and Linux.
Vasya is evolving from a CLI MVP into a broader desktop personal AI system with tasks, calendar, future note workflows, and specialized agents.

Current version: `0.5.3`

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
- tray or menu bar style control for the desktop shell
- more natural conversational UX with follow-up turns and a faster chat path
- a child-friendly voice game mode through a dedicated game agent
- local notes memory with Obsidian export
- a faster two-stage STT pipeline
- STT quality profiles and smarter recovery UX
- avatar skin presets, custom palette import/export, and custom avatar image support
- tool registry with dispatch-based routing
- orchestrator routing policy layer
- agent-to-agent handoff rules
- unified local memory API (snapshot/search)
- managed user profile memory (remember/forget/recall) with local persistence

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
- run in desktop background and start voice capture by hotkey
- show a floating avatar widget with click-to-talk states
- control the desktop shell through a tray icon
- show more natural intermediate response states
- delete all tasks with voice confirmation
- play kid-friendly voice games: words, hide and seek, riddles, guess the animal, and repeat after me
- personalize Vasya through built-in skins, a custom palette, or a custom avatar image
- manage personal memory by voice and clear it from settings with confirmation

Example commands:
- `Add a task to buy a lamp`
- `What tasks do I have?`
- `Add a meeting with Sasha tomorrow at 6 PM`
- `Show my events for March 30`
- `Be quiet`
- `Exit`

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

Desktop shell:

```bash
python main.py
```

Headless background hotkey mode:

```bash
python scripts/hotkey_daemon.py
```

Desktop avatar widget MVP:

```bash
python scripts/avatar_widget.py
```

Notes:
- `python main.py` now starts the desktop shell
- left click starts one voice interaction
- global hotkey also works inside the widget process
- drag moves the avatar on screen
- tray click toggles avatar visibility
- launch at login on macOS can be enabled from Vasya's menu or via `python scripts/autostart_macos.py install`
- tray menu can start listening or quit Vasya
- tray and avatar menu now also expose size, position, hotkey, and tray-click settings
- Vasya now uses a built-in procedural live avatar by default
- built-in skins can be switched directly from settings
- the current palette can be exported to JSON and imported back as a custom skin
- a custom PNG, SVG, JPG, JPEG, or WEBP avatar image can be selected directly from settings
- child mode can temporarily switch Vasya to the child skin without losing the manual skin selection
- `AVATAR_IMAGE_PATH` still works as a fallback if you want to preconfigure an image from the environment
- widget position is restored between launches
- response bubble is shown next to the avatar during listening, thinking, speaking, and errors
- right click opens the avatar context menu

Current platform focus:
- the working MVP is currently oriented around macOS
- future roadmap includes Windows and Linux support

## Configuration

Main settings live in `config/settings.py`.

Example values:

```env
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3
OLLAMA_FAST_MODEL=llama3
OLLAMA_REASONING_MODEL=llama3
OLLAMA_FAST_THINK=false
OLLAMA_FAST_TEMPERATURE=0.1
OLLAMA_FAST_NUM_PREDICT=256
AUDIO_FILENAME=input.wav
RECORD_SECONDS=5
WHISPER_MODEL=base
WHISPER_PARTIAL_MODEL=base
WHISPER_FINAL_MODEL=large-v3-turbo
STT_PARTIAL_BEAM_SIZE=1
STT_FINAL_BEAM_SIZE=5

TTS_VOICE=Milena
TTS_RATE=185
TTS_BACKEND=auto
TTS_PROFILE=ruslan_direct
PIPER_COMMAND=piper
PIPER_MODEL_PATH=storage/voices/ru_RU-ruslan-medium.onnx
PIPER_SPEAKER=
PIPER_LENGTH_SCALE=1.0
TTS_STATE_FILE=storage/tts_settings.json
VOICE_INPUT_BACKEND=auto
HOTKEY_COMBINATION=<cmd>+<option>+<space>
HOTKEY_EXIT_COMBINATION=<cmd>+<option>+q
AVATAR_IMAGE_PATH=
AVATAR_SKIN=classic
AVATAR_SIZE=210
AVATAR_STATE_FILE=storage/avatar_widget.json
AVATAR_CUSTOM_SKIN_FILE=storage/avatar_custom_skin.json

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

For faster intent parsing:
- `OLLAMA_FAST_MODEL` is used for short assistant commands
- `OLLAMA_FAST_THINK=false` disables reasoning on the fast path
- keep `OLLAMA_FAST_NUM_PREDICT` small, for example `128` or `256`

For faster and more accurate speech recognition:
- keep `WHISPER_PARTIAL_MODEL` fast, for example `base`
- set `WHISPER_FINAL_MODEL` to a stronger model such as `large-v3-turbo`
- use `STT_PARTIAL_BEAM_SIZE=1` for quicker partial recognition
- keep `STT_FINAL_BEAM_SIZE=5` for better final accuracy

Voice selection:

```bash
python -m voice.tts --list-profiles
python -m voice.tts --list-voices
python -m voice.tts --profile ruslan_direct --text "Hello, this is a voice test"
```

Voice profiles:
- `ruslan_direct` — male, fast and direct

System voice commands:
- `Be quiet`
- `Stop speaking`
- `Exit`
- `Close assistant`

Alternative TTS path:
- `say` is still the simplest built-in macOS option
- `auto` now prefers `piper` if the command is installed and `PIPER_MODEL_PATH` is configured
- `piper` can be forced explicitly with `TTS_BACKEND=piper`
- for `piper`, configure at least `PIPER_MODEL_PATH`
- on first speech, Vasya prints which TTS backend is actually active
- for Russian local TTS, you can fetch the current voice with `python scripts/setup_piper_ru.py --voices ruslan`

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
- no Notion integration yet
- Obsidian is still export-focused, not a full sync layer
- no specialized code or writing agents yet
- no simple Windows or Linux installation path yet
- no full user-imported character pack system yet

## Version Path

- `v0.3.x`: core voice MVP, local storage, calendar/tasks, Google Calendar, hotkey mode
- `v0.4.0`: first desktop widget MVP with assistant state layer and click-to-talk avatar
- `v0.4.1`: improved conversational UX, voice confirmations, faster chat path, safer bulk task deletion
- `v0.4.2`: child game mode and a dedicated game agent
- `v0.4.3`: notes, local memory, and Obsidian export
- `v0.4.4`: voice responsiveness, child-safe UX, and improved game flow
- `v0.4.5`: two-stage STT, STT quality profiles, smarter follow-up recovery, and clearer task/calendar clarifications
- `v0.4.6`: avatar personalization, built-in skins, custom palette import/export, custom avatar image overrides, and child-mode auto skin switching
- `v0.4.7`: first-run onboarding, onboarding dialog, and checklist/progress polish
- `v0.5.0`: product shell polish (hover tooltip, status indicator)
- `v0.5.1`: mini hover tooltips per state
- `v0.5.2`: tool registry, routing policy layer, handoff rules, and unified memory API
- `v0.5.3`: managed user profile memory, fast-path memory commands, and settings-based personal memory cleanup
- `v0.5.x`: a more cohesive desktop shell, richer avatar behavior, and user-imported visual themes
- `v0.6.x`: easier installation, starting with a Windows setup path and then Linux
- `v0.7.x`: Notion adapter plus deeper Obsidian workflows
- `v0.8.x`: code agent and writing/research agent
- `v1.0`: cross-platform Vasya with easy installation, skins, Obsidian + Notion, stable voice UX, and multi-agent workflows

## Planned Direction

Near-term goals:
- a more polished desktop shell around the current widget MVP
- richer avatar personalization and user-imported visual styles
- continued improvements to voice understanding and recovery UX
- easier installation, starting with a Windows setup path
- Notion as a second adapter on top of the local-first core

## What 1.0 Means

For Vasya, `1.0` should mean a real product, not just another MVP:
- macOS, Windows, and Linux work at a practical level
- installation is close to “download and run”
- the desktop shell feels stable and intentional
- voice UX is fast and predictable
- Vasya can be personalized through skins
- Vasya can also be personalized through user images and custom palette-based themes
- the local core remains the source of truth
- Obsidian and Notion work as external adapters and views
- multiple specialized agents are available instead of only one general assistant

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
