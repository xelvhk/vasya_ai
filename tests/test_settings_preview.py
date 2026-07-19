from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QWidget

    from scripts.ui.settings_preview import AvatarPreview
except ImportError:  # pragma: no cover - depends on optional desktop deps
    QApplication = None
    AvatarPreview = None
    QWidget = object


class _FakeAvatarWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._avatar_size = 210
        self._avatar_skin = "classic"
        self._auto_child_skin = True
        self._avatar_opacity = 1.0
        self._idle_motion_enabled = False
        self._avatar = None

    def _paint_preview_image_avatar(self, *args, **kwargs) -> None:
        return None

    def _paint_preview_character(self, *args, **kwargs) -> None:
        return None


@unittest.skipUnless(AvatarPreview is not None, "PySide6 is not installed")
class SettingsPreviewTests(unittest.TestCase):
    def test_avatar_preview_exposes_update_preview_api(self) -> None:
        self.assertTrue(callable(AvatarPreview.update_preview))

    def test_avatar_preview_effective_skin_respects_child_mode_toggle(self) -> None:
        app = QApplication.instance() or QApplication([])
        _ = app

        preview = AvatarPreview(_FakeAvatarWidget())

        preview.update_preview(
            size=210,
            skin_id="minimal",
            child_mode_enabled=True,
            auto_child_skin=True,
            opacity=1.0,
            idle_motion=False,
        )

        self.assertEqual(preview._effective_skin_id(), "child")

        preview.update_preview(
            size=210,
            skin_id="minimal",
            child_mode_enabled=True,
            auto_child_skin=False,
            opacity=1.0,
            idle_motion=False,
        )

        self.assertEqual(preview._effective_skin_id(), "minimal")

    def test_avatar_preview_character_scale_is_bounded(self) -> None:
        app = QApplication.instance() or QApplication([])
        _ = app

        preview = AvatarPreview(_FakeAvatarWidget())

        preview.update_preview(
            size=80,
            skin_id="classic",
            child_mode_enabled=False,
            auto_child_skin=True,
            opacity=1.0,
            idle_motion=False,
        )
        self.assertEqual(preview._character_scale(), 0.82)

        preview.update_preview(
            size=320,
            skin_id="classic",
            child_mode_enabled=False,
            auto_child_skin=True,
            opacity=1.0,
            idle_motion=False,
        )
        self.assertEqual(preview._character_scale(), 1.18)


if __name__ == "__main__":
    unittest.main()
