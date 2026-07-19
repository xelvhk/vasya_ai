from __future__ import annotations

import math

from assistant.state import AssistantStateName
from PySide6.QtGui import QColor

from .avatar_skins import avatar_skin_spec


def glow_color(state_name: AssistantStateName, skin_id: str | None = None) -> str:
    skin = avatar_skin_spec(skin_id)
    if state_name == AssistantStateName.LISTENING:
        return skin["glow_listening"]
    if state_name == AssistantStateName.THINKING:
        return skin["glow_thinking"]
    if state_name == AssistantStateName.SPEAKING:
        return skin["glow_speaking"]
    if state_name == AssistantStateName.ERROR:
        return skin["glow_error"]
    return skin["glow_idle"]


def animation_speed(state_name: AssistantStateName, skin_id: str | None = None) -> float:
    skin = avatar_skin_spec(skin_id)
    if state_name == AssistantStateName.LISTENING:
        speed = 0.12
    elif state_name == AssistantStateName.THINKING:
        speed = 0.08
    elif state_name == AssistantStateName.SPEAKING:
        speed = 0.20
    elif state_name == AssistantStateName.ERROR:
        speed = 0.22
    else:
        speed = 0.05
    return speed * float(skin.get("motion_speed", 1.0))


def animated_glow(
    state_name: AssistantStateName,
    pulse: float,
    skin_id: str | None = None,
) -> QColor:
    skin = avatar_skin_spec(skin_id)
    base = QColor(glow_color(state_name, skin_id))
    if state_name == AssistantStateName.LISTENING:
        alpha = 125 + int(42 * (0.55 + 0.45 * math.sin(pulse * 1.15)))
    elif state_name == AssistantStateName.THINKING:
        alpha = 104 + int(24 * (0.5 + 0.5 * math.sin(pulse * 0.72)))
    elif state_name == AssistantStateName.SPEAKING:
        alpha = 128 + int(72 * abs(math.sin(pulse * 1.85)))
    elif state_name == AssistantStateName.ERROR:
        alpha = 120 + int(80 * abs(math.sin(pulse * 2.0)))
    else:
        alpha = 90 + int(12 * (0.5 + 0.5 * math.sin(pulse * 0.55)))
    base.setAlpha(int(alpha * float(skin.get("glow_alpha", 1.0))))
    return base


def avatar_bob_offset(
    state_name: AssistantStateName,
    bob: float,
    skin_id: str | None = None,
) -> float:
    skin = avatar_skin_spec(skin_id)
    if state_name == AssistantStateName.LISTENING:
        value = -1.8 * abs(math.sin(bob * 0.9))
    elif state_name == AssistantStateName.THINKING:
        value = -1.0 * math.sin(bob * 0.8)
    elif state_name == AssistantStateName.SPEAKING:
        value = -3.8 * abs(math.sin(bob * 1.35))
    elif state_name == AssistantStateName.ERROR:
        value = 1.2 * math.sin(bob * 2.4)
    else:
        value = -0.45 * math.sin(bob * 0.7)
    return value * float(skin.get("motion_bob", 1.0))


def shadow_width_delta(
    state_name: AssistantStateName,
    pulse: float,
    skin_id: str | None = None,
) -> float:
    skin = avatar_skin_spec(skin_id)
    if state_name == AssistantStateName.SPEAKING:
        value = -7 * abs(math.sin(pulse * 1.6))
    elif state_name == AssistantStateName.LISTENING:
        value = -3 * abs(math.sin(pulse * 0.9))
    else:
        value = -2 * abs(math.sin(pulse))
    return value * float(skin.get("motion_bob", 1.0))


def highlight_color(
    state_name: AssistantStateName,
    pulse: float,
    skin_id: str | None = None,
) -> QColor:
    color = QColor(glow_color(state_name, skin_id))
    color.setAlpha(105 + int(35 * abs(math.sin(pulse))))
    return color


def eye_gaze_offset(state_name: AssistantStateName, pulse: float) -> tuple[float, float]:
    if state_name == AssistantStateName.LISTENING:
        return (0.04 * math.sin(pulse * 0.8), -0.03)
    if state_name == AssistantStateName.THINKING:
        return (0.07 * math.sin(pulse * 0.45), -0.05)
    if state_name == AssistantStateName.SPEAKING:
        return (0.03 * math.sin(pulse * 1.4), 0.01)
    if state_name == AssistantStateName.ERROR:
        return (0.08 * math.sin(pulse * 2.0), -0.02)
    return (0.025 * math.sin(pulse * 0.5), 0.0)


def speaking_eye_squint(state_name: AssistantStateName, pulse: float) -> float:
    if state_name == AssistantStateName.SPEAKING:
        return 0.9 + 0.1 * abs(math.sin(pulse * 1.6))
    if state_name == AssistantStateName.LISTENING:
        return 1.02
    return 1.0


def listening_face_lift(state_name: AssistantStateName, pulse: float) -> float:
    if state_name == AssistantStateName.LISTENING:
        return -1.4 - 0.6 * abs(math.sin(pulse * 0.95))
    return 0.0


def mouth_expression(
    state_name: AssistantStateName,
    pulse: float,
    smile_bounce: float = 0.0,
) -> tuple[float, float, float, float]:
    if state_name == AssistantStateName.LISTENING:
        return (202, 134, -1.1, 1.04)
    if state_name == AssistantStateName.THINKING:
        return (215, 112, 0.5 * math.sin(pulse * 0.7), 0.96)
    if state_name == AssistantStateName.SPEAKING:
        return (
            198,
            145 + 18 * abs(math.sin(pulse * 1.9)),
            -1.2 * abs(math.sin(pulse * 1.5)),
            1.05,
        )
    if state_name == AssistantStateName.ERROR:
        return (225, 86, 1.6 * abs(math.sin(pulse * 1.8)), 0.9)
    return (
        205 - int(6 * smile_bounce),
        130 + int(26 * smile_bounce),
        -1.8 * smile_bounce,
        1.0 + 0.08 * smile_bounce,
    )


def blink_scale(state_name: AssistantStateName, pulse: float) -> float:
    if state_name == AssistantStateName.THINKING:
        return 0.90 + 0.10 * abs(math.sin(pulse * 0.55))
    if state_name == AssistantStateName.ERROR:
        return 0.88 + 0.12 * abs(math.sin(pulse * 1.6))

    blink_wave = max(0.0, math.sin(pulse * 0.62))
    if blink_wave > 0.985:
        return 0.22
    if blink_wave > 0.95:
        return 0.55
    return 1.0
