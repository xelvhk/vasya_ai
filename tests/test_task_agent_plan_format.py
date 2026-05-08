from __future__ import annotations

import unittest
from unittest.mock import patch

from core.models import IntentResult
from agents.task_agent import handle_task_intent


class TaskAgentPlanFormatTests(unittest.TestCase):
    def test_compact_plan_today_for_many_tasks(self) -> None:
        intent = IntentResult(intent="get_tasks", data={"datetime": "сегодня"})
        fake_tasks = [
            {"id": "1", "task": "Задача 1", "datetime": None},
            {"id": "2", "task": "Задача 2", "datetime": None},
            {"id": "3", "task": "Задача 3", "datetime": None},
            {"id": "4", "task": "Задача 4", "datetime": None},
        ]
        with patch("agents.task_agent.get_tasks", return_value=fake_tasks):
            response = handle_task_intent(intent)
        self.assertIn("План:", response)
        self.assertIn("И еще 1", response)

    def test_compact_plan_week_for_short_list(self) -> None:
        intent = IntentResult(intent="get_tasks", data={"datetime": "на этой неделе"})
        fake_tasks = [
            {"id": "1", "task": "Сделать обзор", "datetime": None},
            {"id": "2", "task": "Отправить отчет", "datetime": None},
        ]
        with patch("agents.task_agent.get_tasks", return_value=fake_tasks):
            response = handle_task_intent(intent)
        self.assertTrue(response.startswith("План:"))


if __name__ == "__main__":
    unittest.main()
