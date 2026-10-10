from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class TrayActionSpec:
    key: str
    label: str


TRAY_GROUPS: tuple[tuple[str | None, tuple[TrayActionSpec, ...]], ...] = (
    (None, (
        TrayActionSpec("toggle_avatar", "Скрыть Васю"),
        TrayActionSpec("listen", "Начать слушать"),
        TrayActionSpec("text_command", "Написать Васе..."),
    )),
    ("Радио", (
        TrayActionSpec("radio_toggle", "Включить / пауза"),
        TrayActionSpec("radio_warm", "Тёплый"),
        TrayActionSpec("radio_rain", "Дождь"),
        TrayActionSpec("radio_night", "Ночь"),
        TrayActionSpec("radio_pulse", "Ритм"),
        TrayActionSpec("radio_mix", "Микс"),
        TrayActionSpec("radio_quieter", "Тише"),
        TrayActionSpec("radio_louder", "Громче"),
    )),
    ("Память", (
        TrayActionSpec("memory_status", "Memory Center..."),
        TrayActionSpec("memory_recent", "Последнее в памяти..."),
        TrayActionSpec("memory_search", "Поиск в памяти..."),
        TrayActionSpec("memory_digest", "Последний дайджест памяти..."),
        TrayActionSpec("memory_digests", "История дайджестов..."),
        TrayActionSpec("memory_sync", "Синхронизировать память"),
        TrayActionSpec("clear_memory", "Очистить личную память..."),
    )),
    ("Ещё", (
        TrayActionSpec("quick_commands", "Быстрые команды"),
        TrayActionSpec("mic_test", "Тест микрофона"),
        TrayActionSpec("speed_diagnostics", "Диагностика скорости..."),
    )),
    (None, (TrayActionSpec("settings", "Настройки..."),)),
    (None, (TrayActionSpec("quit", "Закрыть Васю"),)),
)


def build_tray_menu(
    *,
    action_cls: type,
    menu_cls: type,
    owner: Any,
    callbacks: dict[str, Callable[[], None]],
) -> tuple[Any, dict[str, Any]]:
    menu = menu_cls()
    actions: dict[str, Any] = {}
    for group_index, (group_label, specs) in enumerate(TRAY_GROUPS):
        if group_index in {4, 5}:
            menu.addSeparator()
        target = menu.addMenu(group_label) if group_label else menu
        for spec in specs:
            action = action_cls(spec.label, owner)
            action.triggered.connect(callbacks[spec.key])
            target.addAction(action)
            actions[spec.key] = action
    return menu, actions
