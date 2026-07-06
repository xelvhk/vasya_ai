from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ComboLike(Protocol):
    def addItem(self, label: str, value: int | str) -> None:
        ...


@dataclass(frozen=True)
class SettingsOption:
    label: str
    value: int | str


AVATAR_SIZE_OPTIONS: tuple[SettingsOption, ...] = (
    SettingsOption("Маленький", 180),
    SettingsOption("Средний", 210),
    SettingsOption("Большой", 270),
)

TRAY_CLICK_OPTIONS: tuple[SettingsOption, ...] = (
    SettingsOption("Показать или скрыть Васю", "toggle"),
    SettingsOption("Начать слушать", "listen"),
)


def populate_combo_options(combo: ComboLike, options: tuple[SettingsOption, ...]) -> None:
    for option in options:
        combo.addItem(option.label, option.value)
