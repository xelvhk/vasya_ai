from __future__ import annotations

from typing import Protocol


class ActionRowLayoutLike(Protocol):
    def addWidget(self, widget) -> None:
        ...

    def addStretch(self, stretch: int) -> None:
        ...


class FormLayoutLike(Protocol):
    def setLabelAlignment(self, alignment) -> None:
        ...

    def setFormAlignment(self, alignment) -> None:
        ...

    def setHorizontalSpacing(self, spacing: int) -> None:
        ...

    def setVerticalSpacing(self, spacing: int) -> None:
        ...


class RangedValueInputLike(Protocol):
    def setRange(self, minimum: int, maximum: int) -> None:
        ...

    def setValue(self, value: int) -> None:
        ...


class DecimalValueInputLike(Protocol):
    def setRange(self, minimum: float, maximum: float) -> None:
        ...

    def setSingleStep(self, step: float) -> None:
        ...

    def setValue(self, value: float) -> None:
        ...

    def setSuffix(self, suffix: str) -> None:
        ...


class SliderValueInputLike(Protocol):
    def setMinimum(self, minimum: int) -> None:
        ...

    def setMaximum(self, maximum: int) -> None:
        ...

    def setSingleStep(self, step: int) -> None:
        ...

    def setValue(self, value: int) -> None:
        ...


class CheckboxInputLike(Protocol):
    def setChecked(self, checked: bool) -> None:
        ...

    def setToolTip(self, tooltip: str) -> None:
        ...


def configure_settings_form_layout(
    layout: FormLayoutLike,
    *,
    label_alignment,
    form_alignment,
) -> None:
    layout.setLabelAlignment(label_alignment)
    layout.setFormAlignment(form_alignment)
    layout.setHorizontalSpacing(16)
    layout.setVerticalSpacing(12)


def add_action_row_widgets(
    layout: ActionRowLayoutLike,
    widgets,
) -> None:
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch(1)


def configure_ranged_value_input(
    control: RangedValueInputLike,
    *,
    minimum: int,
    maximum: int,
    value: int,
) -> None:
    control.setRange(minimum, maximum)
    control.setValue(value)


def configure_decimal_value_input(
    control: DecimalValueInputLike,
    *,
    minimum: float,
    maximum: float,
    step: float,
    value: float,
    suffix: str,
) -> None:
    control.setRange(minimum, maximum)
    control.setSingleStep(step)
    control.setValue(value)
    control.setSuffix(suffix)


def configure_slider_value_input(
    control: SliderValueInputLike,
    *,
    minimum: int,
    maximum: int,
    step: int,
    value: int,
) -> None:
    control.setMinimum(minimum)
    control.setMaximum(maximum)
    control.setSingleStep(step)
    control.setValue(value)


def configure_checkbox_input(
    control: CheckboxInputLike,
    *,
    checked: bool,
    tooltip: str | None = None,
) -> None:
    control.setChecked(checked)
    if tooltip is not None:
        control.setToolTip(tooltip)
