from __future__ import annotations

import unittest

from assistant.state import AssistantState, AssistantStateName
from scripts.ui.avatar_text import (
    bubble_text,
    hover_hint_text,
    state_label,
    tray_tooltip_text,
    visible_response_bubble_text,
)


class AvatarTextTests(unittest.TestCase):
    def test_state_label_keeps_russian_state_copy(self) -> None:
        self.assertEqual(state_label(AssistantStateName.LISTENING), "слушает")
        self.assertEqual(state_label(AssistantStateName.THINKING), "думает")
        self.assertEqual(state_label(AssistantStateName.SPEAKING), "говорит")
        self.assertEqual(state_label(AssistantStateName.ERROR), "ошибка")
        self.assertEqual(state_label(AssistantStateName.IDLE), "в покое")

    def test_bubble_text_prefers_state_message_then_defaults(self) -> None:
        self.assertEqual(
            bubble_text(AssistantState(AssistantStateName.SPEAKING, "  привет  ")),
            "привет",
        )
        self.assertEqual(bubble_text(AssistantState(AssistantStateName.LISTENING)), "Слушаю...")
        self.assertEqual(bubble_text(AssistantState(AssistantStateName.THINKING)), "Думаю...")
        self.assertEqual(bubble_text(AssistantState(AssistantStateName.SPEAKING)), "Отвечаю...")
        self.assertEqual(bubble_text(AssistantState(AssistantStateName.ERROR)), "Что-то пошло не так")
        self.assertEqual(bubble_text(AssistantState(AssistantStateName.IDLE)), "")

    def test_visible_response_bubble_text_preserves_hide_conditions_and_truncation(self) -> None:
        long_message = "а" * 111
        state = AssistantState(AssistantStateName.SPEAKING, long_message)

        self.assertIsNone(
            visible_response_bubble_text(
                state,
                show_response_bubble=False,
                widget_visible=True,
            )
        )
        self.assertIsNone(
            visible_response_bubble_text(
                AssistantState(AssistantStateName.IDLE, "привет"),
                show_response_bubble=True,
                widget_visible=True,
            )
        )
        self.assertEqual(
            visible_response_bubble_text(
                state,
                show_response_bubble=True,
                widget_visible=True,
            ),
            f"{'а' * 107}...",
        )

    def test_hover_hint_text_keeps_state_specific_copy(self) -> None:
        self.assertEqual(
            hover_hint_text(
                AssistantState(AssistantStateName.IDLE),
                thinking_seconds=0,
                voice_health_hint="Скорость: ок",
            ),
            "Клик — говорить • ПКМ — меню\nСкорость: ок",
        )
        self.assertEqual(
            hover_hint_text(
                AssistantState(AssistantStateName.THINKING),
                thinking_seconds=0,
                voice_health_hint="unused",
            ),
            "Думаю… 1с",
        )
        self.assertEqual(
            hover_hint_text(
                AssistantState(AssistantStateName.ERROR, "слишком тихо"),
                thinking_seconds=5,
                voice_health_hint="unused",
            ),
            "Слишком тихо — скажи громче",
        )

    def test_tray_tooltip_text_keeps_thinking_and_detail_truncation(self) -> None:
        self.assertEqual(
            tray_tooltip_text(
                AssistantState(AssistantStateName.IDLE),
                thinking_seconds=0,
                voice_health_hint="Скорость: ок",
            ),
            "Вася AI • Скорость: ок",
        )
        self.assertEqual(
            tray_tooltip_text(
                AssistantState(AssistantStateName.THINKING),
                thinking_seconds=8,
                voice_health_hint="unused",
            ),
            "Вася AI [думает] 8с",
        )

        long_message = " ".join(["ответ"] * 20)
        tooltip = tray_tooltip_text(
            AssistantState(AssistantStateName.SPEAKING, long_message),
            thinking_seconds=0,
            voice_health_hint="unused",
        )

        self.assertTrue(tooltip.startswith("Вася AI [говорит] • "))
        self.assertLessEqual(len(tooltip.split(" • ", 1)[1]), 56)
        self.assertTrue(tooltip.endswith("..."))


if __name__ == "__main__":
    unittest.main()
