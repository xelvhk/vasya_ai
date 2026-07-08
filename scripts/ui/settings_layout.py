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
