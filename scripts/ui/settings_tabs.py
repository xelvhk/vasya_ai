from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SettingsTabSpec:
    tab_id: str
    label: str


SETTINGS_TABS: tuple[SettingsTabSpec, ...] = (
    SettingsTabSpec("appearance", "Внешний вид"),
    SettingsTabSpec("behavior", "Поведение"),
    SettingsTabSpec("integrations", "Интеграции"),
)
