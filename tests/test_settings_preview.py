from __future__ import annotations

import unittest

try:
    from scripts.ui.settings_preview import AvatarPreview
except ImportError:  # pragma: no cover - depends on optional desktop deps
    AvatarPreview = None


@unittest.skipUnless(AvatarPreview is not None, "PySide6 is not installed")
class SettingsPreviewTests(unittest.TestCase):
    def test_avatar_preview_exposes_update_preview_api(self) -> None:
        self.assertTrue(callable(AvatarPreview.update_preview))


if __name__ == "__main__":
    unittest.main()
