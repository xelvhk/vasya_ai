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

## Voice and weather city

Open **Настройки → Поведение** from Vasya's right-click menu. **Голос Васи**
selects a voice profile; **Сейчас используется** shows the actual TTS engine.
With `TTS_BACKEND=auto` and the `silero_aidar` profile selected, Vasya uses
Silero v5.5 `aidar` at 1.25× speed when its local model, PyTorch Python, and
`ffmpeg` are available. The model stays loaded
between replies. Otherwise Vasya uses Piper when available, then the macOS
system voice. Run `python scripts/setup_silero_ru.py` to download the verified
model into local storage, then set `SILERO_PYTHON` to a Python interpreter with
`torch` and `numpy`. The model stays outside Git. Silero publishes it under
[CC BY-NC-SA 4.0](https://github.com/snakers4/silero-models/blob/master/LICENSE):
credit Silero and retain the license when redistributing the model; obtain
separate rights for commercial use. An XTTS profile
alone does not install XTTS. To prepare the bundled Russian Piper profile, run
`python scripts/setup_piper_ru.py --voices ruslan` in the project's virtual
environment. Existing installations keep their saved voice choice; select
`Айдар — основной голос Васи` in Settings to switch. Then restart Vasya and
check the actual engine in Settings.

In the same tab, **Город утреннего шоу** controls the weather city. Enter
`Saint-Petersburg` for Saint Petersburg and apply the settings. `Moscow` is
only the fallback when no city has been saved.

## Optional API Mode
```bash
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8787 --reload
```
