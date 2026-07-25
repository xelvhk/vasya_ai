# v0.7.0 Release Checklist

Target: first macOS installable artifact for Vasya AI.

## Build Artifact

Run from the repository root on macOS:

```bash
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python scripts/build_macos_app.py
.venv/bin/python scripts/smoke_macos_app.py
.venv/bin/python scripts/smoke_macos_app.py --launch --timeout 3
.venv/bin/python scripts/package_macos_app.py
```

Expected local output:

- `.app`: `build/packaging/dist/Vasya AI.app`
- unsigned ZIP: `build/packaging/release/Vasya-AI-macos-unsigned.zip`

## Quality Gates

Before running `doctor --strict`, make sure `.env` has a non-empty
`VASYA_API_AUTH_TOKEN` when `VASYA_API_REQUIRE_AUTH=true`.

```bash
.venv/bin/python -m unittest discover tests
.venv/bin/python -m compileall agents apps assistant config core interfaces repositories scripts services tests utils voice main.py
.venv/bin/python scripts/doctor.py --strict --quiet
git diff --check
```

GitHub Actions CI must be green on the release commit before tagging.

## Manual Smoke

- Unzip `Vasya-AI-macos-unsigned.zip` into a clean directory.
- Launch `Vasya AI.app`.
- Confirm the desktop shell appears or starts hidden according to saved config.
- Confirm the app does not overwrite an existing `.env`.
- Confirm first-run setup problems are actionable through docs or `doctor`.

## External Prerequisites To Mention

- Ollama remains external and the configured model must be pulled separately.
- macOS microphone permission is required for voice input.
- macOS Accessibility permission is required for global hotkeys and desktop actions.
- Optional integrations still require their own credentials and local token setup.

## Known Limitations

- The first artifact is unsigned and not notarized.
- DMG packaging is still a follow-up; ZIP is the first downloadable shape.
- Packaged `doctor` access is not yet integrated into the app bundle.
- Windows and Linux installers are out of scope for `v0.7.0`.
