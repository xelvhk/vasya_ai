from __future__ import annotations

import unittest
from unittest.mock import patch

from core.intent_parser import parse_intent


class TaskWriteGuardTests(unittest.TestCase):
    def test_model_cannot_create_task_from_a_question(self) -> None:
        model_result = '{"intent":"create_task","data":{"task":"первостепенные задачи"}}'
        with patch("core.intent_parser.generate", return_value=model_result):
            result = parse_intent("С чего мне начать по задачам?")
        self.assertEqual(result.intent, "unknown")

    def test_model_can_create_task_from_explicit_request(self) -> None:
        model_result = '{"intent":"create_task","data":{"task":"подготовить отчет"}}'
        with patch("core.intent_parser.generate", return_value=model_result):
            result = parse_intent("Пожалуйста, добавь мне задачу подготовить отчет")
        self.assertEqual(result.intent, "create_task")


if __name__ == "__main__":
    unittest.main()
