from __future__ import annotations

import unittest

from scripts.ui.tray_menu import build_tray_menu


class _FakeSignal:
    def __init__(self) -> None:
        self.callback = None

    def connect(self, callback) -> None:
        self.callback = callback


class _FakeAction:
    def __init__(self, label: str, owner) -> None:
        self.label = label
        self.owner = owner
        self.triggered = _FakeSignal()


class _FakeMenu:
    def __init__(self, label: str = "") -> None:
        self.label = label
        self.items: list[object] = []

    def addAction(self, action: _FakeAction) -> None:
        self.items.append(action)

    def addSeparator(self) -> None:
        self.items.append("separator")

    def addMenu(self, label: str):
        submenu = _FakeMenu(label)
        self.items.append(submenu)
        return submenu


class AvatarTrayMenuTests(unittest.TestCase):
    def test_build_tray_menu_keeps_action_order_and_callbacks(self) -> None:
        owner = object()
        calls: list[str] = []
        callbacks = {
            "toggle_avatar": lambda: calls.append("toggle"),
            "listen": lambda: calls.append("listen"),
            "text_command": lambda: calls.append("text"),
            "radio_toggle": lambda: calls.append("radio"),
            "radio_warm": lambda: calls.append("warm"),
            "radio_rain": lambda: calls.append("rain"),
            "radio_night": lambda: calls.append("night"),
            "radio_pulse": lambda: calls.append("pulse"),
            "radio_mix": lambda: calls.append("mix"),
            "radio_quieter": lambda: calls.append("quieter"),
            "radio_louder": lambda: calls.append("louder"),
            "quick_commands": lambda: calls.append("quick"),
            "mic_test": lambda: calls.append("mic"),
            "speed_diagnostics": lambda: calls.append("speed"),
            "memory_status": lambda: calls.append("memory-status"),
            "memory_recent": lambda: calls.append("memory-recent"),
            "memory_search": lambda: calls.append("memory-search"),
            "memory_digest": lambda: calls.append("memory-digest"),
            "memory_digests": lambda: calls.append("memory-digests"),
            "memory_sync": lambda: calls.append("memory-sync"),
            "settings": lambda: calls.append("settings"),
            "clear_memory": lambda: calls.append("clear-memory"),
            "quit": lambda: calls.append("quit"),
        }

        menu, actions = build_tray_menu(
            action_cls=_FakeAction,
            menu_cls=_FakeMenu,
            owner=owner,
            callbacks=callbacks,
        )

        labels = [item.label if isinstance(item, (_FakeAction, _FakeMenu)) else item for item in menu.items]
        self.assertEqual(
            labels,
            [
                "Скрыть Васю",
                "Начать слушать",
                "Написать Васе...",
                "Радио",
                "Память",
                "Ещё",
                "separator",
                "Настройки...",
                "separator",
                "Закрыть Васю",
            ],
        )
        radio = next(item for item in menu.items if isinstance(item, _FakeMenu) and item.label == "Радио")
        self.assertEqual([item.label for item in radio.items if isinstance(item, _FakeAction)], [
            "Включить / пауза", "Тёплый", "Дождь", "Ночь", "Ритм", "Микс", "Тише", "Громче",
        ])
        self.assertIs(actions["toggle_avatar"].owner, owner)
        actions["listen"].triggered.callback()
        actions["radio_toggle"].triggered.callback()
        actions["quit"].triggered.callback()
        self.assertEqual(calls, ["listen", "radio", "quit"])


if __name__ == "__main__":
    unittest.main()
