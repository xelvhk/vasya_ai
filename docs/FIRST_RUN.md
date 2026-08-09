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
- source-checkout `storage/`, `storage/memory_wiki`, and `storage/voices` directories
- packaged app-data profile under the platform path documented in `docs/APP_DATA.md`

## Existing Data Migration
Packaged builds do not write into the application bundle or launch directory. Before removing an old checkout, migrate its `.env` and `storage/` data with the copy-only command in `docs/APP_DATA.md`.

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
