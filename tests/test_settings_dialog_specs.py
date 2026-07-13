from __future__ import annotations

import unittest

from scripts.ui.settings_dialog_specs import (
    SETTINGS_DIALOG_BUTTON_LABELS,
    SETTINGS_DIALOG_CHECKBOX_LABELS,
    SETTINGS_DIALOG_HEADER_TEXTS,
    SETTINGS_DIALOG_OBJECT_NAMES,
    SETTINGS_DIALOG_PLACEHOLDERS,
    SETTINGS_DIALOG_ROW_LABELS,
    SETTINGS_DIALOG_TOOLTIPS,
)


class SettingsDialogSpecsTests(unittest.TestCase):
    def test_object_names_match_stylesheet_selectors(self) -> None:
        self.assertEqual(SETTINGS_DIALOG_OBJECT_NAMES.tabs, "settingsTabs")
        self.assertEqual(SETTINGS_DIALOG_OBJECT_NAMES.tab_page, "settingsTabPage")

    def test_header_texts_keep_expected_copy(self) -> None:
        self.assertEqual(SETTINGS_DIALOG_HEADER_TEXTS.window_title, "Настройки Васи")
        self.assertEqual(SETTINGS_DIALOG_HEADER_TEXTS.title, "Настройки Васи")
        self.assertEqual(
            SETTINGS_DIALOG_HEADER_TEXTS.subtitle,
            "Управление поведением виджета, автозапуском "
            "и голосовой активацией.",
        )

    def test_row_labels_keep_expected_core_settings(self) -> None:
        self.assertEqual(SETTINGS_DIALOG_ROW_LABELS.avatar_size, "Размер Васи")
        self.assertEqual(
            SETTINGS_DIALOG_ROW_LABELS.avatar_opacity,
            "Прозрачность Васи",
        )
        self.assertEqual(SETTINGS_DIALOG_ROW_LABELS.voice_profile, "Голос Васи")
        self.assertEqual(SETTINGS_DIALOG_ROW_LABELS.dictation_target, "Режим диктовки")
        self.assertEqual(SETTINGS_DIALOG_ROW_LABELS.hotkey, "Горячая клавиша")

    def test_button_labels_keep_expected_actions(self) -> None:
        self.assertEqual(
            SETTINGS_DIALOG_BUTTON_LABELS.import_skin,
            "Импорт палитры...",
        )
        self.assertEqual(
            SETTINGS_DIALOG_BUTTON_LABELS.reset_morning_show,
            "Сбросить на сегодня",
        )
        self.assertEqual(
            SETTINGS_DIALOG_BUTTON_LABELS.clear_memory,
            "Очистить личную память...",
        )

    def test_checkbox_labels_keep_expected_actions(self) -> None:
        self.assertEqual(
            SETTINGS_DIALOG_CHECKBOX_LABELS.show_bubble,
            "Показывать пузырь ответа",
        )
        self.assertEqual(
            SETTINGS_DIALOG_CHECKBOX_LABELS.auto_interrupt,
            "Прерывать озвучивание новой "
            "голосовой командой",
        )
        self.assertEqual(
            SETTINGS_DIALOG_CHECKBOX_LABELS.launch_at_login,
            "Запускать при входе",
        )

    def test_placeholders_and_tooltips_keep_guidance_text(self) -> None:
        self.assertEqual(
            SETTINGS_DIALOG_PLACEHOLDERS.morning_show_city,
            "Город для погоды, например Moscow",
        )
        self.assertEqual(
            SETTINGS_DIALOG_TOOLTIPS.auto_interrupt_hits_normal,
            "Рекомендуется: 2 подтверждения",
        )


if __name__ == "__main__":
    unittest.main()
