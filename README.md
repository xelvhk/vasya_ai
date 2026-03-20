# Vasya MVP

Language: **English** | [Русский](README.ru.md)

Local AI assistant for desktop, voice commands, tasks, calendar, and future agent workflows.

A local voice AI assistant for MacBook.

At the moment, this is an MVP project that can:
- record voice commands from the microphone
- transcribe speech locally
- send text to a local LLM via Ollama
- understand simple commands
- add tasks
- add events
- store data locally in JSON

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
├── storage/
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

CALENDAR_STORAGE_FILE = "storage/calendar.json"
TASK_STORAGE_FILE = "storage/tasks.json"

## How it works

The current pipeline looks like this:

Voice → audio recording → Whisper STT → text → Ollama → intent parsing → router → agent → local action → response

Data storage

For now, data is stored locally:
 • tasks — in storage/tasks.json
 • events — in storage/calendar.json

These files are not pushed to the repository.

Current MVP limitations

The project is still at the MVP stage, so there are some limitations:
 • no wake word
 • no always-listening mode
 • no proper Google Calendar API integration yet
 • no task synchronization with external services
 • date/time parsing is still basic
 • no long-term memory
 • no code agent

Planned next steps

Possible next improvements:
 • Google Calendar integration
 • proper date and time parsing
 • response speech via macOS say or Piper
 • always-listening mode
 • wake word “Vasya”
 • integration with Obsidian / Todoist / Google Tasks
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