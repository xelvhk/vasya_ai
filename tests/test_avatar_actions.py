from __future__ import annotations

import unittest

from assistant.state import AssistantStateName
from scripts.ui.avatar_actions import text_command_decision, voice_activation_decision


class AvatarActionsTests(unittest.TestCase):
    def test_voice_activation_starts_when_no_interaction_is_running(self) -> None:
        decision = voice_activation_decision(
            interaction_locked=False,
            current_state_name=AssistantStateName.IDLE,
        )

        self.assertEqual(decision.action, "start")
        self.assertEqual(decision.log_event, "widget_activation_started")
        self.assertFalse(decision.stop_speaking)
        self.assertFalse(decision.queue_activation)

    def test_voice_activation_interrupts_speaking_when_busy(self) -> None:
        decision = voice_activation_decision(
            interaction_locked=True,
            current_state_name=AssistantStateName.SPEAKING,
        )

        self.assertEqual(decision.action, "interrupt_speaking")
        self.assertEqual(decision.log_event, "widget_activation_interrupt_speaking")
        self.assertEqual(decision.state_name, AssistantStateName.IDLE)
        self.assertEqual(
            decision.state_message,
            "Остановила озвучивание. Нажми еще раз, чтобы говорить.",
        )
        self.assertTrue(decision.stop_speaking)

    def test_voice_activation_queues_when_busy_and_not_speaking(self) -> None:
        decision = voice_activation_decision(
            interaction_locked=True,
            current_state_name=AssistantStateName.THINKING,
        )

        self.assertEqual(decision.action, "queue")
        self.assertEqual(
            decision.log_event,
            "widget_activation_queued reason=interaction_in_progress",
        )
        self.assertEqual(decision.state_name, AssistantStateName.THINKING)
        self.assertEqual(
            decision.state_message,
            "Заканчиваю текущий запрос и сразу начну слушать.",
        )
        self.assertTrue(decision.queue_activation)

    def test_text_command_starts_when_no_interaction_is_running(self) -> None:
        decision = text_command_decision(
            interaction_locked=False,
            has_cancel_event=False,
        )

        self.assertEqual(decision.action, "start")
        self.assertFalse(decision.queue_command)

    def test_text_command_replaces_current_when_cancel_event_exists(self) -> None:
        decision = text_command_decision(
            interaction_locked=True,
            has_cancel_event=True,
        )

        self.assertEqual(decision.action, "replace_current")
        self.assertEqual(decision.state_name, AssistantStateName.THINKING)
        self.assertEqual(
            decision.state_message,
            "Останавливаю текущий ответ и переключаюсь на новую команду...",
        )
        self.assertTrue(decision.stop_speaking)
        self.assertTrue(decision.queue_command)
        self.assertTrue(decision.cancel_current)

    def test_text_command_waits_when_busy_without_cancel_event(self) -> None:
        decision = text_command_decision(
            interaction_locked=True,
            has_cancel_event=False,
        )

        self.assertEqual(decision.action, "wait")
        self.assertEqual(decision.state_name, AssistantStateName.THINKING)
        self.assertEqual(
            decision.state_message,
            "Секунду, сначала закончу текущий запрос.",
        )
        self.assertFalse(decision.stop_speaking)
        self.assertFalse(decision.queue_command)


if __name__ == "__main__":
    unittest.main()
