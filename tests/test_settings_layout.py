from __future__ import annotations

import unittest

from scripts.ui.settings_layout import (
    add_action_row_widgets,
    configure_decimal_value_input,
    configure_ranged_value_input,
    configure_settings_form_layout,
    configure_slider_value_input,
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


class _FakeDecimalInput:
    def __init__(self) -> None:
        self.calls = []

    def setRange(self, minimum: float, maximum: float) -> None:
        self.calls.append(("range", minimum, maximum))

    def setSingleStep(self, step: float) -> None:
        self.calls.append(("step", step))

    def setValue(self, value: float) -> None:
        self.calls.append(("value", value))

    def setSuffix(self, suffix: str) -> None:
        self.calls.append(("suffix", suffix))


class _FakeSliderInput:
    def __init__(self) -> None:
        self.calls = []

    def setMinimum(self, minimum: int) -> None:
        self.calls.append(("minimum", minimum))

    def setMaximum(self, maximum: int) -> None:
        self.calls.append(("maximum", maximum))

    def setSingleStep(self, step: int) -> None:
        self.calls.append(("step", step))

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

    def test_configure_decimal_value_input_applies_range_step_value_and_suffix(self) -> None:
        control = _FakeDecimalInput()

        configure_decimal_value_input(
            control,
            minimum=0.5,
            maximum=3.0,
            step=0.1,
            value=1.5,
            suffix=" s",
        )

        self.assertEqual(
            control.calls,
            [
                ("range", 0.5, 3.0),
                ("step", 0.1),
                ("value", 1.5),
                ("suffix", " s"),
            ],
        )

    def test_configure_slider_value_input_applies_bounds_step_and_value(self) -> None:
        control = _FakeSliderInput()

        configure_slider_value_input(
            control,
            minimum=70,
            maximum=100,
            step=5,
            value=85,
        )

        self.assertEqual(
            control.calls,
            [
                ("minimum", 70),
                ("maximum", 100),
                ("step", 5),
                ("value", 85),
            ],
        )


if __name__ == "__main__":
    unittest.main()
