from __future__ import annotations

import unittest

from scripts.ui.settings_layout import (
    add_action_row_widgets,
    configure_ranged_value_input,
    configure_settings_form_layout,
)


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


class _FakeActionLayout:
    def __init__(self) -> None:
        self.calls = []

    def addWidget(self, widget) -> None:
        self.calls.append(("widget", widget))

    def addStretch(self, stretch: int) -> None:
        self.calls.append(("stretch", stretch))


class _FakeRangedInput:
    def __init__(self) -> None:
        self.calls = []

    def setRange(self, minimum: int, maximum: int) -> None:
        self.calls.append(("range", minimum, maximum))

    def setValue(self, value: int) -> None:
        self.calls.append(("value", value))


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

    def test_add_action_row_widgets_adds_widgets_before_trailing_stretch(self) -> None:
        layout = _FakeActionLayout()

        add_action_row_widgets(layout, ("import", "export", "reset"))

        self.assertEqual(
            layout.calls,
            [
                ("widget", "import"),
                ("widget", "export"),
                ("widget", "reset"),
                ("stretch", 1),
            ],
        )

    def test_configure_ranged_value_input_sets_range_before_value(self) -> None:
        control = _FakeRangedInput()

        configure_ranged_value_input(control, minimum=1, maximum=6, value=2)

        self.assertEqual(
            control.calls,
            [
                ("range", 1, 6),
                ("value", 2),
            ],
        )


if __name__ == "__main__":
    unittest.main()
