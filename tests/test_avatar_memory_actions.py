from __future__ import annotations

import unittest

from scripts.ui.avatar_memory_actions import (
    memory_search_actions,
    selected_memory_search_action,
)


class AvatarMemoryActionsTests(unittest.TestCase):
    def test_memory_search_actions_build_file_and_url_actions_in_order(self) -> None:
        actions = memory_search_actions(
            {
                "items": [
                    {
                        "title": "Daily Note",
                        "markdown_path": "/tmp/daily.md",
                        "url": "https://example.test/daily",
                    },
                    {"title": "", "markdown_path": "/tmp/untitled.md"},
                    "ignored",
                ]
            }
        )

        self.assertEqual(
            [(action.label, action.kind, action.target) for action in actions],
            [
                ("Файл: Daily Note", "file", "/tmp/daily.md"),
                ("URL: Daily Note", "url", "https://example.test/daily"),
                ("Файл: Untitled memory", "file", "/tmp/untitled.md"),
            ],
        )

    def test_memory_search_actions_truncates_long_titles_like_widget_menu(self) -> None:
        long_title = "Очень длинное название заметки про память и проекты"

        actions = memory_search_actions(
            {"items": [{"title": long_title, "url": "https://example.test"}]}
        )

        self.assertEqual(
            actions[0].label,
            "URL: Очень длинное название заметки про памя...",
        )

    def test_memory_search_actions_respects_item_limit_before_filtering(self) -> None:
        result = {
            "items": [
                {"title": "one", "url": "https://one.test"},
                {"title": "two", "url": "https://two.test"},
                {"title": "three", "url": "https://three.test"},
            ]
        }

        actions = memory_search_actions(result, limit=2)

        self.assertEqual([action.target for action in actions], ["https://one.test", "https://two.test"])

    def test_selected_memory_search_action_returns_matching_action(self) -> None:
        actions = memory_search_actions(
            {"items": [{"title": "Daily Note", "markdown_path": "/tmp/daily.md"}]}
        )

        self.assertEqual(selected_memory_search_action(actions, "missing"), None)
        self.assertEqual(
            selected_memory_search_action(actions, "Файл: Daily Note"),
            actions[0],
        )


if __name__ == "__main__":
    unittest.main()
