# First Run Checklist

Use this checklist after cloning Vasya AI on macOS.

## Quick Path
```bash
bash scripts/setup_mac.sh
source .venv/bin/activate
ollama pull llama3
python scripts/doctor.py
python main.py
```

## What Setup Prepares
- `.venv` virtual environment
- Python dependencies from `requirements.txt`
- `.env` from `.env.example` with a generated `VASYA_API_AUTH_TOKEN`
- local `storage/`, `storage/memory_wiki`, and `storage/voices` directories

## First-Run Checks
- Ollama is installed and the configured model is available
- macOS microphone permission is granted when requested
- macOS Accessibility permission is granted for hotkeys and desktop actions when requested
- `python scripts/doctor.py` reports no blocking failures
- `python main.py` starts the desktop shell

## Optional API Mode
```bash
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8787 --reload
```
