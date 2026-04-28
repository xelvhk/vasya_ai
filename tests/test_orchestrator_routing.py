from __future__ import annotations

import unittest
from unittest.mock import patch

from assistant.confirmations import confirmation_store
from core.orchestrator import process_text_detailed


class OrchestratorRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        confirmation_store.clear()

    def tearDown(self) -> None:
        confirmation_store.clear()

    def test_pending_confirmation_has_priority_over_project_idea_clarification(self) -> None:
        confirmation_store.set("delete_all_tasks")
        with patch(
            "core.orchestrator.has_pending_project_idea_clarification",
            return_value=True,
        ):
            with patch(
                "core.orchestrator.continue_project_idea_clarification",
                return_value="Уточню еще один пункт по идее",
            ) as idea_mock:
                with patch(
                    "core.orchestrator.confirm_delete_all_tasks",
                    return_value="Удалила все задачи.",
                ) as confirm_mock:
                    result = process_text_detailed("да")

        self.assertEqual(result.intent, "delete_tasks")
        self.assertEqual(result.response, "Удалила все задачи.")
        self.assertEqual(result.role, "task_agent")
        self.assertFalse(result.needs_followup)
        confirm_mock.assert_called_once()
        idea_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
