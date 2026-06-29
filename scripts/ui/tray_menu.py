from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class TrayActionSpec:
    key: str
    label: str
    separator_after: bool = False


TRAY_ACTIONS: tuple[TrayActionSpec, ...] = (
    TrayActionSpec("toggle_avatar", "Скрыть Васю"),
    TrayActionSpec("listen", "Начать слушать"),
    TrayActionSpec("text_command", "Текстовая команда..."),
    TrayActionSpec("quick_commands", "Быстрые команды"),
    TrayActionSpec("mic_test", "Тест микрофона"),
    TrayActionSpec("speed_diagnostics", "Диагностика скорости..."),
    TrayActionSpec("memory_status", "Memory Center..."),
    TrayActionSpec("memory_recent", "Последнее в памяти..."),
    TrayActionSpec("memory_search", "Поиск в памяти..."),
    TrayActionSpec("memory_digest", "Последний дайджест памяти..."),
    TrayActionSpec("memory_digests", "История дайджестов..."),
    TrayActionSpec("memory_sync", "Синхронизировать память"),
    TrayActionSpec("settings", "Настройки..."),
    TrayActionSpec("clear_memory", "Очистить личную память...", separator_after=True),
    TrayActionSpec("quit", "Закрыть Васю"),
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
    for spec in TRAY_ACTIONS:
        action = action_cls(spec.label, owner)
        action.triggered.connect(callbacks[spec.key])
        menu.addAction(action)
        actions[spec.key] = action
        if spec.separator_after:
            menu.addSeparator()
    return menu, actions
