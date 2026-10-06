# Pixel Vasya desktop companion: first slice

## Objective

Use the user's pixel-art technician reference as the visual direction for the
existing macOS/PySide6 avatar. Vasya should remain a usable assistant widget
while gaining a small, recognisable character and purposeful ambient motion.

## Assumptions and scope

- The human character in the reference is the primary visual direction. The
  reference collage is not itself a usable sprite sheet; project assets are
  original frames on transparent backgrounds.
- Keep the existing chat, voice, hotkeys, tray, bubbles, drag and saved position.
- The first slice walks only within the current screen's available bottom edge.
  No screen capture, window inspection, cursor tracking, or model calls drive
  ambient motion.
- Existing assistant states take priority over ambient walking. Reduced motion
  and an explicit switch disable roaming. Pixel Vasya is the desktop character.
- No new Python UI framework or runtime dependency.

## First-slice behavior

1. The desktop widget renders a consistent pixel character at a compact size.
2. While idle and enabled, he occasionally walks a short bounded distance,
   pauses, then returns to idle animation. User interaction immediately stops
   the walk. A manual drag remains authoritative and preserves its saved position.
3. Listening, thinking, speaking, and error states retain visible feedback.
   The art may use a neutral fallback when a dedicated frame is not ready.
4. On multiple monitors, walking stays on the monitor containing the widget.
   Screen edges, menu bar, and Dock are respected.
5. Users can disable roaming without disabling chat or status animation.

## Acceptance and verification

- Unit tests cover movement bounds, pause/disable rules, user interruption,
  and state precedence.
- Sprite atlas tests cover grid/frame loading and fallback behavior.
- Focused Qt smoke verifies transparent rendering, dragging, and no movement
  outside the available screen; run the full Python suite and syntax checks.
- Visually inspect the idle, walk, listening, thinking, and result frames at
  intended widget size. Report measured CPU and memory only after a runtime test.

## Trying the first slice

The desktop widget uses **Пиксельный Вася** automatically. Choose the
**Компактный** size if preferred. The character moves to the bottom of the current screen.
Click Vasya to open the compact question window. Type and press Enter or the
orange send button; the microphone button starts the existing voice flow. The
answer remains readable in the window until it is closed. The dark violet and
warm amber colors follow the pixel showcase image on the Vasya landing.

Right-click the widget and use **Настройки → Прогулка по экрану** to pause or
resume short walks, or **Погулять сейчас** to start one immediately. Dragging
Vasya away from the bottom leaves him stationary; dragging him back allows
walking after the next idle delay. macOS Reduce Motion
also disables roaming. The chat, microphone, and hotkeys remain available.

For text commands, the work pose appears after the pipeline resolves the
intent. Speaking uses the success pose. Agent jobs started outside the desktop
text pipeline do not yet publish lifecycle events to this widget.

## Later slices

Add dedicated work/result art tied to actual task lifecycle events and optional
sleep/sit behavior after the first slice works well during daily desktop use.
