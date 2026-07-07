from __future__ import annotations

import unittest

from scripts.ui.settings_layout import configure_settings_form_layout


class _FakeFormLayout:
    def __init__(self) -> None:
        self.label_alignment = None
        self.form_alignment = None
        self.horizontal_spacing = None
        self.vertical_spacing = None

    def setLabelAlignment(self, alignment) -> None:
        self.label_alignment = alignment

    def setFormAlignment(self, alignment) -> None:
        self.form_alignment = alignment

    def setHorizontalSpacing(self, spacing: int) -> None:
        self.horizontal_spacing = spacing

    def setVerticalSpacing(self, spacing: int) -> None:
        self.vertical_spacing = spacing


class SettingsLayoutTests(unittest.TestCase):
    def test_configure_settings_form_layout_applies_common_spacing_and_alignment(self) -> None:
        layout = _FakeFormLayout()

        configure_settings_form_layout(
            layout,
            label_alignment="left",
            form_alignment="top",
        )

        self.assertEqual(layout.label_alignment, "left")
        self.assertEqual(layout.form_alignment, "top")
        self.assertEqual(layout.horizontal_spacing, 16)
        self.assertEqual(layout.vertical_spacing, 12)


if __name__ == "__main__":
    unittest.main()
