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
- settings dialog copy/spec metadata lives in `scripts/ui/settings_dialog_specs.py`;
- the `SettingsDialog` shell now lives in `scripts/ui/settings_dialog.py`;
- tray menu construction has a dedicated helper in `scripts/ui/tray_menu.py`;
- avatar state persistence helpers stay GUI-free in `scripts/ui/avatar_state.py`;
- each helper extraction has focused unit coverage and has passed GitHub CI.

What still needs care:
- `scripts/avatar_widget.py` is still the main desktop shell entry point and
  still owns the avatar runtime, rendering, tray, onboarding, and command flows;
- `SettingsDialog` still mixes behavior, voice tuning, integration checks,
  signals, and persistence wiring inside one class;
- moving PySide widget construction outside the dialog layer too early would
  increase regression risk;
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
- Extract settings dialog constants/specs.
- Extract settings dialog shell.
- Split settings dialog tab builders inside the dialog shell.
- Split settings dialog behavior wiring inside the dialog shell.
- Extract avatar rendering visual helper formulas.
- Split avatar preview skin and scale helpers.
- Extract image avatar paint geometry helpers.
- Extract character avatar core geometry helpers.

## Next PR Sequence

1. `refactor(ui): isolate avatar rendering`
   - Continue with paint/rendering helper isolation.

2. `refactor(voice): split voice backends`
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
