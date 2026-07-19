from __future__ import annotations

import unittest

from assistant.state import AssistantStateName

try:
    from scripts.ui.avatar_rendering import (
        animated_glow,
        animation_speed,
        avatar_bob_offset,
        blink_scale,
        glow_color,
        mouth_expression,
    )
except ImportError:  # pragma: no cover - depends on optional desktop deps
    animated_glow = None
    animation_speed = None
    avatar_bob_offset = None
    blink_scale = None
    glow_color = None
    mouth_expression = None


@unittest.skipUnless(glow_color is not None, "PySide6 is not installed")
class AvatarRenderingTests(unittest.TestCase):
    def test_glow_color_uses_state_and_skin(self) -> None:
        self.assertEqual(glow_color(AssistantStateName.IDLE, "classic"), "#4f8fff")
        self.assertEqual(
            glow_color(AssistantStateName.LISTENING, "minimal"),
            "#d5e6ff",
        )
        self.assertEqual(glow_color(AssistantStateName.ERROR, "sunset"), "#ff5f76")

    def test_animation_speed_applies_skin_motion_speed(self) -> None:
        classic = animation_speed(AssistantStateName.SPEAKING, "classic")
        child = animation_speed(AssistantStateName.SPEAKING, "child")

        self.assertAlmostEqual(classic, 0.20)
        self.assertAlmostEqual(child, 0.20 * 1.18)

    def test_avatar_bob_offset_applies_skin_motion_bob(self) -> None:
        classic = avatar_bob_offset(AssistantStateName.LISTENING, 1.4, "classic")
        minimal = avatar_bob_offset(AssistantStateName.LISTENING, 1.4, "minimal")

        self.assertAlmostEqual(minimal, classic * 0.7)

    def test_animated_glow_applies_skin_alpha(self) -> None:
        classic = animated_glow(AssistantStateName.IDLE, 0.0, "classic")
        minimal = animated_glow(AssistantStateName.IDLE, 0.0, "minimal")

        self.assertEqual(classic.name(), "#4f8fff")
        self.assertEqual(classic.alpha(), 96)
        self.assertEqual(minimal.name(), "#b7c8ea")
        self.assertEqual(minimal.alpha(), int(96 * 0.8))

    def test_mouth_expression_keeps_state_specific_shapes(self) -> None:
        self.assertEqual(mouth_expression(AssistantStateName.LISTENING, 0.0), (202, 134, -1.1, 1.04))
        self.assertEqual(mouth_expression(AssistantStateName.IDLE, 0.0, 0.5), (202, 143, -0.9, 1.04))

    def test_blink_scale_keeps_state_specific_behavior(self) -> None:
        self.assertEqual(blink_scale(AssistantStateName.IDLE, 0.0), 1.0)
        self.assertAlmostEqual(blink_scale(AssistantStateName.THINKING, 0.0), 0.90)


if __name__ == "__main__":
    unittest.main()
