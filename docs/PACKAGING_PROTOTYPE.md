# Packaging Prototype

Status: first local unsigned macOS `.app` prototype built with PyInstaller.

## Command

1. `.venv/bin/python -m pip install -r requirements-build.txt`
2. `.venv/bin/python scripts/build_macos_app.py`

The build script sets `PYINSTALLER_CONFIG_DIR` to `build/packaging/cache` by
default so PyInstaller does not write to `~/Library/Application Support`.

## Output

- App bundle: `build/packaging/dist/Vasya AI.app`
- Onedir payload: `build/packaging/dist/Vasya AI`
- Generated spec/work/cache directories: `build/packaging/spec`,
  `build/packaging/work`, and `build/packaging/cache`
- Local observed size: around 398M for the `.app`, around 794M for the full
  `build/packaging/dist` directory
- Assets are bundled under the app resources and onedir internal payload

## First Build Findings

- Initial build failed when PyInstaller tried to use the user-level
  `~/Library/Application Support/pyinstaller` directory. The script now uses a
  repository-local default cache path.
- PyInstaller emitted non-blocking warnings for conditional platform modules,
  including Windows and X11 imports.
- macOS hotkey dependencies report several optional PyObjC/Quartz imports in
  PyInstaller's warning file. Treat this as a launch-smoke watchlist item.
- Pydantic compatibility warnings should remain on the packaging watchlist while
  the project runs on Python 3.14.

## Not Yet Verified

- Launching the `.app` through Finder or `open`.
- First-run `.env` and storage behavior from inside the bundle.
- macOS microphone and Accessibility permission prompts.
- Ollama/model diagnostics inside the packaged app.
- DMG or ZIP wrapping, signing, and notarization.
