# Vasya UI Design System

This document adapts the visual direction from DESIGN-9.md to an operational,
local-first desktop product. The reference remains useful for its matte dark
surfaces, restrained typography, and hairline borders. Marketing hero layouts,
device mockups, decorative gradients, and oversized editorial spacing do not
belong in Project OS work surfaces.

## Product Principles

- Show project status and the next useful action in the first viewport.
- Keep configuration and credentials out of the primary dashboard flow.
- Prefer dense, scan-friendly rows and grids over promotional sections.
- Use one locale per surface. The current desktop and Control Center locale is
  Russian; future localization must switch the complete surface together.
- Keep private paths, tokens, and user-owned project data local.

## Core Tokens

| Role | Value |
| --- | --- |
| Canvas | #0b0b0b |
| Surface | #151515 |
| Raised surface | #1c1c1c |
| Primary text | #f1f1f1 |
| Muted text | #b3b3b3 |
| Quiet text | #969696 |
| Border | #363636 |
| Strong border | #505050 |
| Ready | #78dba9 |
| Attention | #ffcc66 |
| Error | #ff9f9f |
| UI radius | 8px |
| Minimum pointer target | 44px |

Status colors always appear with a text label. Color is never the only signal.

## Layout

- Maximum content width is 1200px.
- The application header is a compact full-width band.
- Dashboard order is title and actions, metrics, project status, then registry
  management.
- Cards are reserved for repeated project and metric items.
- Sections remain unframed and are separated with spacing or hairline borders.
- Mobile layouts must not scroll horizontally at 320px or wider.

## Components

- Primary actions use a light fill with dark text.
- Secondary and destructive actions use transparent surfaces and clear borders.
- Status chips may use a pill shape; command buttons and panels use an 8px
  radius.
- Dialog actions remain visible, controls are at least 44px high, and server
  errors receive programmatic focus.
- API credentials live in the Connection dialog and use session-scoped browser
  storage only.

## Desktop Parity

PySide settings use the same canvas, surface, text, border, and radius values.
Widget construction remains native Qt, but visual hierarchy should match the
Control Center: neutral surfaces, restrained emphasis, and no decorative
gradients.

## Verification

For every visual slice:

1. Run focused unit and route tests.
2. Verify keyboard focus, dialog focus, and error announcements.
3. Check 390px, 768px, and desktop viewports for overflow and 44px targets.
4. Run the full suite, compileall, and git diff --check.

