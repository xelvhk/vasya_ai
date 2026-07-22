# Packaging Discovery

Status: local repository inventory for the `v0.7.0` macOS installer track. This
document does not choose a packaging tool; it records what the first packaging
prototype must preserve.

## Entrypoints

- Primary desktop entrypoint: `python main.py`.
- `main.py` imports `scripts.avatar_widget.main` and runs the desktop shell.
- If the desktop shell exits with a non-zero `SystemExit`, `main.py` falls back
  to `scripts.hotkey_daemon.main`.
- Optional local API entrypoint remains:
  `python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8787`.

## Runtime Prerequisites

- Python runtime target is 3.11+, matching `scripts/doctor.py` and CI.
- Desktop UI uses `PySide6_Essentials`; packaged builds must include Qt runtime
  plugins and keep the app launchable without an activated repository venv.
- Background hotkeys use `pynput`, so macOS Accessibility permission remains a
  first-run requirement.
- Voice capture/playback and transcription dependencies include
  `sounddevice`, `faster-whisper`, `scipy`, and related audio packages.
- Optional API mode uses `fastapi` and `uvicorn`.
- Optional secure storage uses `keyring`.
- Environment loading uses `python-dotenv`.
- Ollama remains external for the first artifact; users still need the binary,
  a running server, and the selected model.

## Config And Storage

- `.env` is loaded by `config/settings.py` at import time.
- Many runtime paths still default to relative files under `storage/`, including
  avatar state, TTS settings, dictation state, child mode, logs, cache, voices,
  and memory wiki data.
- `AUDIO_FILENAME` defaults to the relative file `input.wav`.
- The first packaging prototype must define a predictable writable working
  directory or introduce a narrow app-data-path adapter before shipping.
- First run must preserve existing `.env` and storage data. It must not
  overwrite a generated `VASYA_API_AUTH_TOKEN`.
- Repository ignore rules already exclude local runtime JSON, DB, log, cache,
  voice, model, and token artifacts under `storage/`.

## Assets To Include

- Runtime avatar assets live under `assets/`, including `assets/vasya_avatar.svg`
  and the `assets/skins/vasya_pro` skin pack.
- The `vasya_pro` skin pack includes `manifest.json`, `preview.png`, and WebP
  frames for idle, listening, speaking, thinking, and error states.
- Generated Finder metadata such as `.DS_Store` should not be bundled.
- User-provided custom skins or images remain user data and should stay outside
  the application bundle.

## Setup And Diagnostics

- Current source-checkout setup starts with `scripts/setup_mac.sh` and
  `scripts/setup_macos.py`.
- `scripts/setup_macos.py` creates `.venv`, preserves or creates `.env`, ensures
  `storage`, `storage/memory_wiki`, and `storage/voices`, optionally installs
  dependencies, checks Ollama, and prints the first-run checklist.
- Packaged users should not need to create `.venv` or run `pip install`.
- Existing diagnostics are in `scripts/doctor.py`.
- CI currently runs dependency install, `compileall`, unit tests, and
  `python scripts/doctor.py --strict --quiet`; it does not build release
  artifacts yet.

## Release Risks And Open Questions

- Relative working-directory assumptions are the main packaging risk.
- PySide/Qt plugin bundling must be validated on macOS before choosing the final
  artifact command.
- Microphone and Accessibility permissions need a clear first-run path.
- Hotkey daemon fallback behavior must remain visible and diagnosable.
- Heavy voice backends, caches, and local models should stay external or
  user-managed for the first artifact.
- Signing and notarization should wait until unsigned artifact creation is
  reproducible.
- The team still needs to decide whether optional API mode is included in the
  desktop artifact or documented as a separate developer/runtime mode.
