# Vasya AI
VAS = (Voice Ai ASsistant)
Language: **English** | [Русский](README.ru.md)

Local AI assistant for desktop, voice commands, tasks, calendar, and future agent workflows.

Current version: `0.2.1`

At the moment, this is an MVP project that can:
- record voice commands from the microphone
- transcribe speech locally
- send text to a local LLM via Ollama
- understand simple commands
- add tasks
- add events
- parse basic Russian date/time phrases for calendar commands
- automatically start Ollama on app startup if the server is not running
- choose a macOS voice for speech output
- store data locally in SQLite

## What already works

Example commands:
- “Add a task to buy a lamp”
- “What tasks do I have?”
- “Add a meeting with Sasha tomorrow at 6 PM”
- “Show my events”

## Tech stack

- Python
- Ollama
- Llama 3
- faster-whisper
- sounddevice
- scipy
- pydantic

## Project structure

```text
ai_pal/
├── main.py
├── test_text.py
├── requirements.txt
├── .env
├── README.md
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
├── voice/
│   ├── __init__.py
│   ├── recorder.py
│   ├── stt.py
│   └── tts.py
│
├── agents/
│   ├── __init__.py
│   ├── calendar_agent.py
│   └── task_agent.py
│
├── services/
│   ├── __init__.py
│   ├── ollama_client.py
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
└── utils/
    ├── __init__.py
    ├── datetime_parser.py
    ├── json_utils.py
    └── logger.py
```
## How to run

1. Clone the project

git clone <repo_url>
cd ai_pal

2. Create a virtual environment

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Install and run Ollama

First, install Ollama:

brew install ollama

Then run the model:

ollama run llama3

If the model is already downloaded, you just need to make sure Ollama is available locally.
On `main.py` startup the app also tries to launch `ollama serve` automatically.

5. Run the project

Text-based test:

python test_text.py

Run the voice workflow:

python main.py

## Configuration

The main settings are located in config/settings.py.

Example:

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"
AUDIO_FILENAME = "input.wav"
RECORD_SECONDS = 5
WHISPER_MODEL = "base"
TTS_VOICE = "Milena"
TTS_RATE = 185

STORAGE_DB_FILE = "storage/vasya.db"
CALENDAR_STORAGE_FILE = "storage/calendar.json"
TASK_STORAGE_FILE = "storage/tasks.json"

Voice selection:

Show available macOS voices:

python -m voice.tts --list-voices

Test a specific voice:

python -m voice.tts --voice Milena --text "Hello, this is a voice test"

Set the default voice in `.env`:

TTS_VOICE=Milena
TTS_RATE=185

## How it works

The current pipeline looks like this:

Voice → audio recording → Whisper STT → text → Ollama → intent parsing → router → agent → local action → response

Data storage

For now, data is stored locally:
 • tasks — in storage/vasya.db
 • events — in storage/vasya.db

The old JSON files are kept only as legacy input for automatic migration into SQLite.
Local data files are not pushed to the repository.

Domain layer

Tasks and events now use simple domain models plus repository classes on top of SQLite.
This keeps agents and services small and makes later integrations easier.

Current MVP limitations

The project is still at the MVP stage, so there are some limitations:
 • no wake word
 • no always-listening mode
 • no proper Google Calendar API integration yet
 • no task synchronization with external services
 • date/time parsing still covers only common cases
 • no long-term memory
 • no code agent

Planned next steps

Possible next improvements:
 • Google Calendar integration
 • integration with Obsidian / Todoist / Google Tasks
 • Piper or another TTS fallback
 • always-listening mode
 • wake word “Vasya”
 • code agent for working with files and projects
 • unified space for multiple AI agents

## Security

The project currently uses local models and local data storage, but when integrating with external services, it will be important to think separately about:
 • token storage
 • calendar access
 • file access
 • agent action logging

# Notes

On macOS, audio recording may require microphone access for Terminal / IDE:
 • System Settings
 • Privacy & Security
 • Microphone

## Author

Xelvhk :computer:

A personal pet project for building a local voice AI assistant with the ability to evolve into a system of personal AI agents.
