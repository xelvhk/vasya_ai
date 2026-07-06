from __future__ import annotations

from dataclasses import dataclass


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
