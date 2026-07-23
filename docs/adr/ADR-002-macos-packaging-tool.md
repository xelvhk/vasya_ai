# ADR-002: Use PyInstaller For The First macOS App Prototype

## Status

Accepted

## Date

2026-07-23

## Context

The `v0.7.0` release track needs a repeatable macOS `.app` prototype before
the project invests in signing, notarization, DMG polish, or cross-platform
installers. The current app is a PySide6 desktop shell launched through
`main.py`, with optional API mode, local storage under `storage/`, bundled
avatar assets under `assets/`, and external runtime prerequisites such as
Ollama plus macOS microphone and Accessibility permissions.

The first packaging tool should:
- work with the current source layout without requiring a project restructure;
- produce a local macOS `.app` bundle for smoke testing;
- allow explicit inclusion of `assets/`;
- keep generated output disposable and ignored;
- leave signing/notarization and installer wrapping as later steps.

## Decision

Use PyInstaller for the first local macOS artifact prototype.

The prototype should use a one-directory, windowed app bundle shape rather than
a one-file bundle:
- initial command shape: `pyinstaller --windowed --onedir --name "Vasya AI" ... main.py`;
- include `assets/` as bundled data;
- keep `build/`, `dist/`, and generated spec files out of source control unless
  a later slice intentionally promotes a reviewed spec file;
- preserve Ollama, large models, generated `.env`, runtime storage, and user
  voice/cache data as external or user-writable state.

## Alternatives Considered

### Briefcase

Briefcase has strong release packaging features for macOS, including `.app`,
DMG, ZIP, and PKG outputs, and it can also package an external `.app` generated
by another tool. This makes it a good candidate for a later release-artifact
stage, especially once signing/notarization is in scope.

Rejected for the first prototype because it expects explicit project packaging
configuration and would make the first slice about app metadata/scaffolding
rather than proving the existing PySide desktop shell can freeze and launch.

### py2app

py2app is macOS-native and purpose-built for creating standalone macOS app
bundles from Python scripts. It remains a reasonable fallback if PyInstaller
cannot handle the current PySide/audio dependency set.

Rejected for the first prototype because its stable workflow is centered on a
`setup.py`/setuptools command path, while the current project does not yet have
packaging metadata. Starting with PyInstaller keeps the first experiment more
local and reversible.

## Consequences

- The next slice can add a local build script for an unsigned disposable `.app`.
- The prototype should validate Qt/PySide plugin collection, asset inclusion,
  startup behavior, and first-run diagnostics before any DMG/signing work.
- PyInstaller output is a prototype artifact, not the final release process by
  itself.
- If PyInstaller proves brittle around Qt plugins, audio/native dependencies, or
  working-directory semantics, write a superseding ADR and switch to py2app or a
  Briefcase-managed/external-app flow.

## References

- PyInstaller usage docs: https://pyinstaller.org/en/stable/usage.html
- Briefcase macOS docs: https://briefcase.beeware.org/en/latest/reference/platforms/macOS/index.html
- Briefcase external app packaging: https://briefcase.beeware.org/en/v0.3.26/how-to/building/external-apps/
- py2app docs: https://py2app.readthedocs.io/en/stable/
