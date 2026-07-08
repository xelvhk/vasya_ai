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

DICTATION_TARGET_OPTIONS: tuple[SettingsOption, ...] = (
    SettingsOption("В активное поле", "active_field"),
    SettingsOption("Через API", "api"),
)

AGENT_ROUTING_PROFILE_OPTIONS: tuple[SettingsOption, ...] = (
    SettingsOption("RolePack v1 (рекомендуется)", "rolepack_v1"),
    SettingsOption("Classic", "classic_v1"),
)

CHAT_PROMPT_PACK_OPTIONS: tuple[SettingsOption, ...] = (
    SettingsOption("Dynamic v1 (рекомендуется)", "dynamic_v1"),
    SettingsOption("Classic", "classic_v1"),
)


def populate_combo_options(combo: ComboLike, options: tuple[SettingsOption, ...]) -> None:
    for option in options:
        combo.addItem(option.label, option.value)
