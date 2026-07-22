from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from assistant.state import AssistantStateName
from scripts.ui.avatar_assets import (
    avatar_state_key,
    cached_avatar_pack_result,
    load_avatar_pack_manifest,
    pack_frames_for_state,
    prepare_avatar_pixmap,
    render_lottie_avatar,
    render_pack_avatar,
    render_svg_avatar,
    resolve_avatar_path,
)


class FakePixmap:
    def __init__(self, path: str) -> None:
        self.path = path

    def isNull(self) -> bool:
        return Path(self.path).name.startswith("missing")

    def scaled(self, width, height, aspect_ratio_mode, transformation_mode):
        return FakeScaledPixmap(
            source=self,
            width=width,
            height=height,
            aspect_ratio_mode=aspect_ratio_mode,
            transformation_mode=transformation_mode,
        )

    @staticmethod
    def fromImage(image):
        return FakeImagePixmap(image)


class FakeScaledPixmap:
    def __init__(self, *, source, width, height, aspect_ratio_mode, transformation_mode) -> None:
        self.source = source
        self.width = width
        self.height = height
        self.aspect_ratio_mode = aspect_ratio_mode
        self.transformation_mode = transformation_mode


class FakeImagePixmap:
    def __init__(self, image) -> None:
        self.image = image


class FakeImage:
    Format_ARGB32 = "argb32"
    Format_ARGB32_Premultiplied = "argb32-premultiplied"

    def __init__(self, *args) -> None:
        self.args = args
        self.filled_with = None

    def isNull(self) -> bool:
        return False

    def copy(self):
        return self

    def fill(self, color) -> None:
        self.filled_with = color


class NullFakeImage(FakeImage):
    def isNull(self) -> bool:
        return True


class FakeLottieAnimation:
    def __init__(self) -> None:
        self.calls = []

    def lottie_animation_render(self, **kwargs):
        self.calls.append(kwargs)
        return b"raw"


class BrokenLottieAnimation:
    def lottie_animation_render(self, **kwargs):
        raise RuntimeError("render failed")


class FakeSvgRenderer:
    rendered = []

    def __init__(self, path: str) -> None:
        self.path = path

    def isValid(self) -> bool:
        return not self.path.endswith("invalid.svg")

    def render(self, painter, rect) -> None:
        FakeSvgRenderer.rendered.append((painter, rect))


class FakePainter:
    def __init__(self, image) -> None:
        self.image = image
        self.hints = []
        self.ended = False

    def setRenderHint(self, hint) -> None:
        self.hints.append(hint)

    def end(self) -> None:
        self.ended = True


class FakeRect:
    def __init__(self, left, top, width, height) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height


class AvatarAssetsTests(unittest.TestCase):
    def test_avatar_state_key_maps_assistant_states_to_pack_states(self) -> None:
        self.assertEqual(avatar_state_key(AssistantStateName.LISTENING), "listening")
        self.assertEqual(avatar_state_key(AssistantStateName.THINKING), "thinking")
        self.assertEqual(avatar_state_key(AssistantStateName.SPEAKING), "speaking")
        self.assertEqual(avatar_state_key(AssistantStateName.ERROR), "error")
        self.assertEqual(avatar_state_key(AssistantStateName.IDLE), "idle")

    def test_resolve_avatar_path_prefers_existing_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            configured = Path(tmp) / "configured.png"
            override = Path(tmp) / "override.png"
            configured.write_text("configured", encoding="utf-8")
            override.write_text("override", encoding="utf-8")

            result = resolve_avatar_path(
                {"avatar_image_path": str(override)},
                str(configured),
            )

            self.assertEqual(result, override)

    def test_resolve_avatar_path_falls_back_to_existing_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            configured = Path(tmp) / "configured.png"
            configured.write_text("configured", encoding="utf-8")

            result = resolve_avatar_path(
                {"avatar_image_path": str(Path(tmp) / "missing.png")},
                str(configured),
            )

            self.assertEqual(result, configured)

    def test_load_avatar_pack_manifest_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text("{not json", encoding="utf-8")

            result = load_avatar_pack_manifest(manifest, FakePixmap)

            self.assertFalse(result.loaded)
            self.assertEqual(result.frames, {})

    def test_load_avatar_pack_manifest_skips_missing_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "states": {
                            "idle": ["idle_01.webp", "missing_idle.webp"],
                            "speaking": ["speaking_01.webp"],
                            "unknown": ["ignored.webp"],
                        },
                        "timing_ms": {"idle": 5, "speaking": 2500},
                    }
                ),
                encoding="utf-8",
            )

            result = load_avatar_pack_manifest(manifest, FakePixmap)

            self.assertTrue(result.loaded)
            self.assertEqual([Path(frame.path).name for frame in result.frames["idle"]], ["idle_01.webp"])
            self.assertEqual([Path(frame.path).name for frame in result.frames["speaking"]], ["speaking_01.webp"])
            self.assertNotIn("unknown", result.frames)
            self.assertEqual(result.timing_ms["idle"], 40)
            self.assertEqual(result.timing_ms["speaking"], 2000)
            self.assertEqual(result.frame_index, {"idle": 0, "speaking": 0})

    def test_cached_avatar_pack_result_restores_valid_payload(self) -> None:
        payload = {
            "frames": {"idle": [object()], "empty": []},
            "timing_ms": {"idle": 260},
        }

        result = cached_avatar_pack_result(payload)

        self.assertIsNotNone(result)
        self.assertEqual(set(result.frames), {"idle"})
        self.assertEqual(result.frame_index, {"idle": 0})

    def test_pack_frames_for_state_falls_back_to_idle(self) -> None:
        idle_frame = object()
        self.assertEqual(
            pack_frames_for_state({"idle": [idle_frame]}, "speaking"),
            [idle_frame],
        )
        self.assertEqual(pack_frames_for_state({}, "speaking"), [])

    def test_render_pack_avatar_uses_state_frame_and_minimum_size(self) -> None:
        first = FakePixmap("first.webp")
        second = FakePixmap("second.webp")

        result = render_pack_avatar(
            frames_by_state={"speaking": [first, second]},
            frame_index={"speaking": 1},
            state_key="speaking",
            size=32,
            empty_pixmap_factory=lambda: FakePixmap("empty"),
            aspect_ratio_mode="keep",
            transformation_mode="smooth",
        )

        self.assertIs(result.source, second)
        self.assertEqual((result.width, result.height), (64, 64))
        self.assertEqual(result.aspect_ratio_mode, "keep")
        self.assertEqual(result.transformation_mode, "smooth")

    def test_prepare_avatar_pixmap_routes_pack_lottie_svg_and_static_avatar(self) -> None:
        path = Path("avatar.png")
        calls = []

        self.assertEqual(
            prepare_avatar_pixmap(
                avatar_path=path,
                avatar_is_pack=True,
                avatar_is_lottie=False,
                avatar_is_svg=False,
                avatar=None,
                state_name=AssistantStateName.SPEAKING,
                width=40,
                height=80,
                pack_renderer=lambda size, state_key: ("pack", size, state_key),
                lottie_renderer=lambda size: ("lottie", size),
                svg_renderer=lambda size: ("svg", size),
                empty_pixmap_factory=lambda: ("empty",),
                aspect_ratio_mode="keep",
                transformation_mode="smooth",
            ),
            ("pack", 80, "speaking"),
        )

        avatar = FakePixmap("avatar.png")
        result = prepare_avatar_pixmap(
            avatar_path=path,
            avatar_is_pack=False,
            avatar_is_lottie=False,
            avatar_is_svg=False,
            avatar=avatar,
            state_name=AssistantStateName.IDLE,
            width=40,
            height=80,
            pack_renderer=lambda size, state_key: calls.append(("pack", size, state_key)),
            lottie_renderer=lambda size: calls.append(("lottie", size)),
            svg_renderer=lambda size: calls.append(("svg", size)),
            empty_pixmap_factory=lambda: ("empty",),
            aspect_ratio_mode="keep",
            transformation_mode="smooth",
        )

        self.assertIs(result.source, avatar)
        self.assertEqual((result.width, result.height), (40, 80))
        self.assertEqual(calls, [])

    def test_render_lottie_avatar_returns_copied_image_pixmap(self) -> None:
        animation = FakeLottieAnimation()

        result = render_lottie_avatar(
            animation=animation,
            frame=3.8,
            total_frames=10,
            size=20,
            image_factory=FakeImage,
            pixmap_cls=FakePixmap,
            image_format=FakeImage.Format_ARGB32,
            empty_pixmap_factory=lambda: FakePixmap("empty"),
            on_error=lambda exc: None,
        )

        self.assertIsInstance(result, FakeImagePixmap)
        self.assertEqual(animation.calls, [{"frame_num": 3, "width": 64, "height": 64}])
        self.assertEqual(result.image.args, (b"raw", 64, 64, 256, FakeImage.Format_ARGB32))

    def test_render_lottie_avatar_returns_empty_on_error_or_null_image(self) -> None:
        errors = []

        broken = render_lottie_avatar(
            animation=BrokenLottieAnimation(),
            frame=0,
            total_frames=1,
            size=128,
            image_factory=FakeImage,
            pixmap_cls=FakePixmap,
            image_format=FakeImage.Format_ARGB32,
            empty_pixmap_factory=lambda: FakePixmap("empty"),
            on_error=errors.append,
        )
        null_image = render_lottie_avatar(
            animation=FakeLottieAnimation(),
            frame=0,
            total_frames=1,
            size=128,
            image_factory=NullFakeImage,
            pixmap_cls=FakePixmap,
            image_format=FakeImage.Format_ARGB32,
            empty_pixmap_factory=lambda: FakePixmap("empty"),
            on_error=errors.append,
        )

        self.assertEqual(broken.path, "empty")
        self.assertEqual(null_image.path, "empty")
        self.assertEqual(len(errors), 1)

    def test_render_svg_avatar_uses_same_canvas_and_rect_geometry(self) -> None:
        FakeSvgRenderer.rendered = []

        result = render_svg_avatar(
            path=Path("avatar.svg"),
            size=100,
            renderer_cls=FakeSvgRenderer,
            image_cls=FakeImage,
            painter_cls=FakePainter,
            pixmap_cls=FakePixmap,
            image_format=FakeImage.Format_ARGB32_Premultiplied,
            transparent_color="transparent",
            antialiasing_hint="antialias",
            smooth_transform_hint="smooth",
            rect_cls=FakeRect,
        )

        self.assertIsInstance(result, FakeImagePixmap)
        image = result.image
        self.assertEqual(image.args, (100, 100, FakeImage.Format_ARGB32_Premultiplied))
        self.assertEqual(image.filled_with, "transparent")
        painter, rect = FakeSvgRenderer.rendered[0]
        self.assertEqual(painter.hints, ["antialias", "smooth"])
        self.assertTrue(painter.ended)
        self.assertEqual((rect.left, rect.top), (-5.0, -10.0))
        self.assertAlmostEqual(rect.width, 110.0)
        self.assertAlmostEqual(rect.height, 112.0)


if __name__ == "__main__":
    unittest.main()
