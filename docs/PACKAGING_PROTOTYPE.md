# Packaging Prototype

Status: first local unsigned macOS `.app` prototype built with PyInstaller.

## Command

1. `.venv/bin/python -m pip install -r requirements-build.txt`
2. `.venv/bin/python scripts/build_macos_app.py`
3. `.venv/bin/python scripts/smoke_macos_app.py`
4. `.venv/bin/python scripts/build_macos_doctor.py`
5. `.venv/bin/python scripts/package_macos_app.py`
6. `.venv/bin/python scripts/smoke_macos_zip.py`

The build script sets `PYINSTALLER_CONFIG_DIR` to `build/packaging/cache` by
default so PyInstaller does not write to `~/Library/Application Support`.

## Output

- App bundle: `build/packaging/dist/Vasya AI.app`
- Onedir payload: `build/packaging/dist/Vasya AI`
- Doctor companion: `build/packaging/doctor-dist/Vasya AI Doctor`
- Unsigned ZIP artifact: `build/packaging/release/Vasya-AI-macos-unsigned.zip`
  with `Vasya AI.app/` and `Vasya AI Doctor/` at the top level
- Generated spec/work/cache directories: `build/packaging/spec`,
  `build/packaging/work`, and `build/packaging/cache`
- Local observed size: around 398M for the `.app`, around 794M for the full
  `build/packaging/dist` directory
- Local observed doctor companion size: around 225M
- Local observed ZIP size with app and doctor companion: around 224M
- Assets are bundled under the app resources and onedir internal payload
- Structure smoke and direct executable launch smoke passed locally
- ZIP smoke verifies the app and doctor companion payloads are present at the
  archive top level
- Doctor companion starts from the packaged executable and reports diagnostic
  issues without import/runtime failures

## First Build Findings

- Initial build failed when PyInstaller tried to use the user-level
  `~/Library/Application Support/pyinstaller` directory. The script now uses a
  repository-local default cache path.
- PyInstaller emitted non-blocking warnings for conditional platform modules,
  including Windows and X11 imports.
- macOS hotkey dependencies report several optional PyObjC/Quartz imports in
  PyInstaller's warning file. Treat this as a launch-smoke watchlist item.
- The bundled executable stayed alive through a 3 second launch smoke.
- The doctor companion reports packaged Python runtime and bundled Python
  dependencies as OK after hidden import coverage for dateparser and Google
  client modules.
- Pydantic compatibility warnings should remain on the packaging watchlist while
  the project runs on Python 3.14.

## Not Yet Verified

- Launching the `.app` through Finder or `open`.
- First-run `.env` and storage behavior from inside the bundle.
- macOS microphone and Accessibility permission prompts.
- Ollama/model diagnostics inside the packaged app.
- Running the doctor companion from an unpacked ZIP directory.
- DMG wrapping, signing, and notarization.

## Unsigned ZIP

Run `.venv/bin/python scripts/package_macos_app.py` after build and smoke checks
to create the first downloadable unsigned macOS artifact. The script stages the
app and doctor companion payloads with `/usr/bin/ditto`, then archives that
staging directory with `/usr/bin/ditto --sequesterRsrc` so macOS resource
metadata is preserved. The resulting archive includes `Vasya AI.app/` and
`Vasya AI Doctor/` at the top level and may include `__MACOSX/` metadata
entries.

Run `.venv/bin/python scripts/smoke_macos_zip.py` after packaging to verify the
ZIP contains the expected top-level app and doctor payloads and does not expose
the temporary `payload/` staging directory.

## Local Smoke

Run `.venv/bin/python scripts/smoke_macos_app.py` after building to verify the
expected `.app` structure, Info.plist metadata, executable bit, and bundled
avatar assets. Use `.venv/bin/python scripts/smoke_macos_app.py --launch` for a
short executable launch smoke that fails on immediate startup crashes and passes
when the GUI process stays alive through the timeout.
