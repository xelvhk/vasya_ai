# UI Refactor Plan

This document tracks the incremental cleanup of the desktop UI layer after the
v0.6.0/v0.6.1 release work. The goal is to reduce `scripts/avatar_widget.py`
without changing product behavior or making review risky.

## Current Review

Status: no merge-blocking issues found in the current UI helper series.

What improved:
- repeated settings option metadata now lives in `scripts/ui/settings_options.py`;
- repeated settings input configuration now lives in `scripts/ui/settings_layout.py`;
- tab metadata lives in `scripts/ui/settings_tabs.py`;
- tray menu construction has a dedicated helper in `scripts/ui/tray_menu.py`;
- avatar state persistence helpers stay GUI-free in `scripts/ui/avatar_state.py`;
- each helper extraction has focused unit coverage and has passed GitHub CI.

What still needs care:
- `scripts/avatar_widget.py` is still the main desktop shell entry point and
  remains too large for comfortable review;
- `SettingsDialog` construction still mixes appearance, behavior, integrations,
  signals, and persistence wiring;
- moving PySide widget construction too early would increase regression risk;
- helper extraction should stop before it turns into generic form-builder code.

## Guardrails

- Keep each PR behavior-preserving unless the PR title says otherwise.
- Keep PySide widget creation inside the dialog layer until a dedicated dialog
  module exists.
- Prefer GUI-free helpers for metadata, value configuration, formatting, and
  small wiring patterns.
- Add or update focused unit tests before wiring a new helper into
  `avatar_widget.py`.
- Run targeted UI helper tests, full unit tests, and `compileall` before opening
  a PR.
- Merge only after GitHub CI is green.

## Completed Slices

- Extract tray menu builder.
- Extract avatar state persistence helpers.
- Extract settings stylesheet.
- Extract settings tab specs.
- Extract appearance size options.
- Extract tray click options.
- Add shared combo option helper.
- Add settings form layout helper.
- Extract integration input specs.
- Extract dictation target options.
- Extract profile combo options.
- Add action row layout helper.
- Add ranged, decimal, slider, and checkbox input helpers.

## Next PR Sequence

1. `refactor(ui): extract settings dialog constants`
   - Move row labels, placeholder strings, tooltip strings, and section labels
     that are pure metadata into `scripts/ui/settings_dialog_specs.py`.
   - Do not move widget construction yet.

2. `refactor(ui): extract settings dialog shell`
   - Create `scripts/ui/settings_dialog.py`.
   - Move the `SettingsDialog` class as-is, keeping imports explicit and tests
     focused on smoke/import behavior.
   - Leave `avatar_widget.py` responsible for launching the desktop widget and
     passing dependencies through existing instance state.

3. `refactor(ui): split settings dialog sections`
   - Split appearance, behavior, and integrations builders after the dialog is
     already isolated.
   - Keep each section PR small enough to review independently.

4. `refactor(ui): isolate avatar rendering`
   - Move paint/rendering helpers and skin preview logic only after settings
     dialog churn is finished.

5. `refactor(voice): split voice backends`
   - Start after UI shell risk is lower.
   - Split Piper/CosyVoice/XTTS/recorder concerns into dedicated modules with
     compatibility imports if needed.

## Definition of Done

A UI refactor slice is done when:
- the diff has one clear responsibility;
- no runtime behavior intentionally changes;
- focused tests cover the extracted helper or module boundary;
- `python -m unittest discover tests` passes locally;
- `python -m compileall ...` passes locally;
- GitHub CI passes on the PR;
- the final PR description names what did not move yet.

## Stop Conditions

Pause the helper-extraction series and reassess if:
- a helper starts accepting too many unrelated arguments;
- a PR needs broad manual GUI testing to prove basic behavior;
- `avatar_widget.py` becomes harder to scan because call sites are more verbose
  than the original code;
- a change requires moving signal ordering, persistence semantics, or platform
  checks in the same PR.
