from __future__ import annotations

import unittest

from scripts.ui.settings_options import (
    AGENT_ROUTING_PROFILE_OPTIONS,
    AVATAR_SIZE_OPTIONS,
    CHAT_PROMPT_PACK_OPTIONS,
    DICTATION_TARGET_OPTIONS,
    TRAY_CLICK_OPTIONS,
    populate_combo_options,
)


class _FakeCombo:
    def __init__(self) -> None:
        self.items: list[tuple[str, int | str]] = []

    def addItem(self, label: str, value: int | str) -> None:
        self.items.append((label, value))


class SettingsOptionsTests(unittest.TestCase):
    def test_avatar_size_options_keep_expected_order_and_values(self) -> None:
        self.assertEqual(
            [(option.label, option.value) for option in AVATAR_SIZE_OPTIONS],
            [
                ("Маленький", 180),
                ("Средний", 210),
                ("Большой", 270),
            ],
        )

    def test_avatar_size_values_are_unique(self) -> None:
        values = [option.value for option in AVATAR_SIZE_OPTIONS]
        self.assertEqual(len(values), len(set(values)))

    def test_tray_click_options_keep_expected_order_and_values(self) -> None:
        self.assertEqual(
            [(option.label, option.value) for option in TRAY_CLICK_OPTIONS],
            [
                ("Показать или скрыть Васю", "toggle"),
                ("Начать слушать", "listen"),
            ],
        )

    def test_dictation_target_options_keep_expected_order_and_values(self) -> None:
        self.assertEqual(
            [(option.label, option.value) for option in DICTATION_TARGET_OPTIONS],
            [
                ("В активное поле", "active_field"),
                ("Через API", "api"),
            ],
        )

    def test_agent_routing_profile_options_keep_expected_order_and_values(self) -> None:
        self.assertEqual(
            [(option.label, option.value) for option in AGENT_ROUTING_PROFILE_OPTIONS],
            [
                ("RolePack v1 (рекомендуется)", "rolepack_v1"),
                ("Classic", "classic_v1"),
            ],
        )

    def test_chat_prompt_pack_options_keep_expected_order_and_values(self) -> None:
        self.assertEqual(
            [(option.label, option.value) for option in CHAT_PROMPT_PACK_OPTIONS],
            [
                ("Dynamic v1 (рекомендуется)", "dynamic_v1"),
                ("Classic", "classic_v1"),
            ],
        )

    def test_populate_combo_options_adds_labels_and_values(self) -> None:
        combo = _FakeCombo()

        populate_combo_options(combo, TRAY_CLICK_OPTIONS)

        self.assertEqual(
            combo.items,
            [
                ("Показать или скрыть Васю", "toggle"),
                ("Начать слушать", "listen"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
