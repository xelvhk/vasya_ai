# Packaging Prototype

Status: first local unsigned macOS `.app` prototype built with PyInstaller.

## Command

1. `.venv/bin/python -m pip install -r requirements-build.txt`
2. `.venv/bin/python scripts/build_macos_app.py`
3. `.venv/bin/python scripts/smoke_macos_app.py`
4. `.venv/bin/python scripts/package_macos_app.py`

The build script sets `PYINSTALLER_CONFIG_DIR` to `build/packaging/cache` by
default so PyInstaller does not write to `~/Library/Application Support`.

## Output

- App bundle: `build/packaging/dist/Vasya AI.app`
- Onedir payload: `build/packaging/dist/Vasya AI`
- Unsigned ZIP artifact: `build/packaging/release/Vasya-AI-macos-unsigned.zip`
- Generated spec/work/cache directories: `build/packaging/spec`,
  `build/packaging/work`, and `build/packaging/cache`
- Local observed size: around 398M for the `.app`, around 794M for the full
  `build/packaging/dist` directory
- Local observed ZIP size: around 145M
- Assets are bundled under the app resources and onedir internal payload
- Structure smoke and direct executable launch smoke passed locally

## First Build Findings

- Initial build failed when PyInstaller tried to use the user-level
  `~/Library/Application Support/pyinstaller` directory. The script now uses a
  repository-local default cache path.
- PyInstaller emitted non-blocking warnings for conditional platform modules,
  including Windows and X11 imports.
- macOS hotkey dependencies report several optional PyObjC/Quartz imports in
  PyInstaller's warning file. Treat this as a launch-smoke watchlist item.
- The bundled executable stayed alive through a 3 second launch smoke.
- Pydantic compatibility warnings should remain on the packaging watchlist while
  the project runs on Python 3.14.

## Not Yet Verified

- Launching the `.app` through Finder or `open`.
- First-run `.env` and storage behavior from inside the bundle.
- macOS microphone and Accessibility permission prompts.
- Ollama/model diagnostics inside the packaged app.
- DMG wrapping, signing, and notarization.

## Unsigned ZIP

Run `.venv/bin/python scripts/package_macos_app.py` after build and smoke checks
to create the first downloadable unsigned macOS artifact. The script uses
`/usr/bin/ditto --keepParent --sequesterRsrc` so the archive preserves the app
bundle directory and macOS resource metadata. The resulting archive includes
`Vasya AI.app/` at the top level and may include `__MACOSX/` metadata entries.

## Local Smoke

Run `.venv/bin/python scripts/smoke_macos_app.py` after building to verify the
expected `.app` structure, Info.plist metadata, executable bit, and bundled
avatar assets. Use `.venv/bin/python scripts/smoke_macos_app.py --launch` for a
short executable launch smoke that fails on immediate startup crashes and passes
when the GUI process stays alive through the timeout.
