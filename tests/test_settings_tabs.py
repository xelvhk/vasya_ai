from __future__ import annotations

import unittest

from scripts.ui.settings_tabs import SETTINGS_TABS


class SettingsTabsTests(unittest.TestCase):
    def test_settings_tabs_keep_expected_order_and_labels(self) -> None:
        self.assertEqual(
            [(tab.tab_id, tab.label) for tab in SETTINGS_TABS],
            [
                ("appearance", "Внешний вид"),
                ("behavior", "Поведение"),
                ("integrations", "Интеграции"),
            ],
        )

    def test_settings_tab_ids_are_unique(self) -> None:
        tab_ids = [tab.tab_id for tab in SETTINGS_TABS]
        self.assertEqual(len(tab_ids), len(set(tab_ids)))


if __name__ == "__main__":
    unittest.main()
