# Packaging Plan

This plan turns the installer milestone in `ROADMAP.md` into small,
reviewable work slices. The first goal is not "all platforms"; it is a
repeatable macOS artifact that proves the desktop shell can be installed and
launched without a repository checkout.

## Target

`v0.7.0`: first macOS installable artifact.

Expected shape:
- a macOS `.app` bundle packaged as `.dmg` or an equivalent release artifact;
- local-first configuration preserved through first run;
- external dependencies documented clearly, especially Ollama, microphone
  permission, Accessibility permission, and optional integrations;
- release artifact produced from a tagged commit by a documented command or CI
  workflow.

## Pre-Release Foundation

Completed: writable runtime state now resolves through `config/app_paths.py` as
defined by `docs/adr/ADR-003-public-app-and-private-user-data.md`. Source
checkouts retain an explicit compatibility layout, while packaged builds use the
platform profile. The copy-only migration command and recovery guidance live in
`docs/APP_DATA.md`.

## Non-Goals For The First Artifact

- Windows and Linux installers.
- App Store distribution.
- Replacing Ollama or bundling large local models.
- Solving signing/notarization before the unsigned local artifact is
  reproducible.
- Changing application behavior or API auth semantics inside a packaging slice.
- Bundling maintainer projects, local databases, tokens, histories, or caches.

## Release Slices

1. Packaging discovery
   - Confirm entrypoint, icon/assets, PySide runtime requirements, storage paths,
     and first-run config behavior.
   - Current inventory: `docs/PACKAGING_DISCOVERY.md`.
   - Packaging tool decision: `docs/adr/ADR-002-macos-packaging-tool.md`.

2. Local macOS artifact prototype
   - Add a local build script that produces a disposable `.app` artifact.
   - Prototype entrypoint: `python scripts/build_macos_app.py --dry-run`.
   - Install build-only packaging dependencies with
     `.venv/bin/python -m pip install -r requirements-build.txt`.
   - First local build result: `docs/PACKAGING_PROTOTYPE.md`.
   - Local bundle smoke: `.venv/bin/python scripts/smoke_macos_app.py`.
   - Keep generated build output ignored.
   - Verify the app launches the desktop shell on the maintainer machine.

3. Packaged first-run diagnostics
   - Make `doctor` runnable for packaged app users, either inside the app flow or
     through a bundled companion command.
   - Companion prototype: `.venv/bin/python scripts/build_macos_doctor.py`.
   - Document the expected output for missing Ollama, permissions, and optional
     integrations.

4. Release artifact packaging
   - Wrap the `.app` into `.dmg` or an equivalent downloadable artifact.
   - First unsigned ZIP wrapper: `.venv/bin/python scripts/package_macos_app.py`.
   - Release checklist: `docs/RELEASE_CHECKLIST_V0_7.md`.
   - Add release notes checklist items for prerequisites and known limitations.

5. Automation and signing path
   - Add CI or a documented release script for artifact creation from tags.
   - Add signing/notarization only after unsigned builds are reproducible.

6. Cross-platform follow-up
   - Start Windows/Linux installer tracks only after macOS packaging is stable.
   - Reuse the same first-run/doctor acceptance criteria where possible.

## Acceptance Criteria

- Writable state resolves to the current user's platform app-data directory.
- Upgrades and reinstalls preserve local projects, settings, and indexed data.
- Release artifacts contain no maintainer-specific records or credentials.
- A clean macOS machine can install and launch Vasya AI without cloning the
  repository or manually creating a virtualenv.
- First run creates or preserves local `.env`, storage directories, and generated
  API auth token safely.
- The packaged app can surface actionable setup problems through `doctor` or an
  equivalent diagnostics path.
- Release instructions identify what is bundled and what remains external.
- The artifact is produced from a tagged commit with a repeatable command or CI
  workflow.
- Existing quality gates still pass before release: unit tests, scoped
  `compileall`, strict doctor smoke, and GitHub Actions CI.

## Open Decisions

- Artifact format: `.dmg` is the likely first downloadable shape, but `.zip`
  may be acceptable for the first unsigned prototype.
- Signing/notarization: required for polished distribution, but intentionally
  later than the first reproducible local artifact.
- Update flow: out of scope for `v0.7.0`; manual download is acceptable.
