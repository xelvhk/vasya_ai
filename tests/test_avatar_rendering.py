from __future__ import annotations

import unittest

from assistant.state import AssistantStateName

try:
    from scripts.ui import avatar_rendering
except ImportError:  # pragma: no cover - depends on optional desktop deps
    avatar_rendering = None

if avatar_rendering is not None:
    animated_glow = avatar_rendering.animated_glow
    animation_speed = avatar_rendering.animation_speed
    avatar_bob_offset = avatar_rendering.avatar_bob_offset
    blink_scale = avatar_rendering.blink_scale
    glow_color = avatar_rendering.glow_color
    image_avatar_draw_position = getattr(avatar_rendering, "image_avatar_draw_position", None)
    image_avatar_highlight_rect = getattr(avatar_rendering, "image_avatar_highlight_rect", None)
    image_avatar_shadow_metrics = getattr(avatar_rendering, "image_avatar_shadow_metrics", None)
    mouth_expression = avatar_rendering.mouth_expression


@unittest.skipUnless(avatar_rendering is not None, "PySide6 is not installed")
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

    def test_image_avatar_shadow_metrics_match_paint_geometry(self) -> None:
        x, y, width, height, alpha = image_avatar_shadow_metrics(
            AssistantStateName.IDLE,
            container_width=210,
            container_height=210,
            pulse=0.0,
            bob=0.0,
            skin_id="classic",
        )

        self.assertEqual((x, y, width, height, alpha), (18.0, 184, 174.0, 14, 65))

    def test_image_avatar_draw_position_uses_bob_offset(self) -> None:
        self.assertEqual(
            image_avatar_draw_position(
                container_width=210,
                container_height=210,
                pixmap_width=222,
                pixmap_height=226,
                bob_offset=-3.8,
            ),
            (-6, -13),
        )

    def test_image_avatar_highlight_rect_tracks_bob_offset(self) -> None:
        self.assertEqual(
            image_avatar_highlight_rect(
                container_width=210,
                container_height=210,
                bob_offset=-3.8,
            ),
            (18, 16.2, 174, 166),
        )


if __name__ == "__main__":
    unittest.main()
