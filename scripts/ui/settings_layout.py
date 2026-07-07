from __future__ import annotations

from typing import Protocol


class FormLayoutLike(Protocol):
    def setLabelAlignment(self, alignment) -> None:
        ...

    def setFormAlignment(self, alignment) -> None:
        ...

    def setHorizontalSpacing(self, spacing: int) -> None:
        ...

    def setVerticalSpacing(self, spacing: int) -> None:
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
