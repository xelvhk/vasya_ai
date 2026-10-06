from __future__ import annotations

import unittest

from utils.intent_fastpaths import detect_fast_intent


class TaskPlanFastpathTests(unittest.TestCase):
    def test_daily_plan_phrase_routes_to_get_tasks_today(self) -> None:
        intent = detect_fast_intent("план на сегодня")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "get_tasks")
        self.assertEqual(intent.data.get("datetime"), "сегодня")

    def test_weekly_plan_phrase_routes_to_get_tasks_week(self) -> None:
        intent = detect_fast_intent("план на неделю")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "get_tasks")
        self.assertIn("неделе", str(intent.data.get("datetime", "")))

    def test_priority_question_reads_tasks_instead_of_creating_one(self) -> None:
        for question in (
            "Какие у меня первостепенные задачи?",
            "Какие сейчас приоритетные задачи?",
            "Что из моих задач сделать в первую очередь?",
        ):
            with self.subTest(question=question):
                intent = detect_fast_intent(question)
                self.assertIsNotNone(intent)
                assert intent is not None
                self.assertEqual(intent.intent, "get_tasks")
                self.assertTrue(intent.data.get("priority_query"))

    def test_explicit_add_task_still_creates_it(self) -> None:
        intent = detect_fast_intent("Добавь задачу подготовить отчет")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "create_task")


if __name__ == "__main__":
    unittest.main()
