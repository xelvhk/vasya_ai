from __future__ import annotations

import unittest
from unittest.mock import patch

from assistant.project_idea_planning import project_idea_planning_store
from services.project_idea_planning_service import (
    continue_project_idea_clarification,
    handle_project_idea_request,
    has_pending_project_idea_clarification,
)


class ProjectIdeaClarificationTests(unittest.TestCase):
    def setUp(self) -> None:
        project_idea_planning_store.clear()

    def tearDown(self) -> None:
        project_idea_planning_store.clear()

    def test_short_idea_starts_clarification(self) -> None:
        response = handle_project_idea_request(idea="приложение для семьи", title="Family App")
        self.assertIn("уточню", response.lower())
        self.assertTrue(has_pending_project_idea_clarification())

    def test_clarification_collects_answers_and_runs_analysis(self) -> None:
        handle_project_idea_request(idea="сервис заметок", title="My Plan")
        r1 = continue_project_idea_clarification("для студентов")
        r2 = continue_project_idea_clarification("web и mobile")
        with patch(
            "services.project_idea_planning_service.analyze_project_idea_to_obsidian",
            return_value="Готово. Записала.",
        ) as analyze_mock:
            r3 = continue_project_idea_clarification("получить 100 активных пользователей")

        self.assertIn("где он будет жить", r1.lower())
        self.assertIn("главный результат", r2.lower())
        self.assertEqual(r3, "Готово. Записала.")
        self.assertFalse(has_pending_project_idea_clarification())
        kwargs = analyze_mock.call_args.kwargs
        self.assertEqual(kwargs["title"], "My Plan")
        self.assertIn("Базовая идея", kwargs["idea"])
        self.assertIn("для студентов", kwargs["idea"])
        self.assertIn("web и mobile", kwargs["idea"])

    def test_clarification_can_be_canceled(self) -> None:
        handle_project_idea_request(idea="сервис задач", title=None)
        response = continue_project_idea_clarification("отмена")
        self.assertIn("отменяю", response.lower())
        self.assertFalse(has_pending_project_idea_clarification())


if __name__ == "__main__":
    unittest.main()
