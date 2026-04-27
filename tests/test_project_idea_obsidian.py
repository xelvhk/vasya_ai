from __future__ import annotations

import unittest
from unittest.mock import patch

from services.github_obsidian_sync_service import analyze_project_idea_to_obsidian
from utils.intent_fastpaths import detect_fast_intent


class ProjectIdeaObsidianTests(unittest.TestCase):
    def test_analyze_project_idea_to_obsidian_requires_longer_idea(self) -> None:
        result = analyze_project_idea_to_obsidian(idea="сделать приложение", title="test")
        self.assertIn("слишком короткая", result.lower())

    def test_analyze_project_idea_to_obsidian_writes_markdown_note(self) -> None:
        idea = "сервис для контроля личных финансов с бюджетами, целями и еженедельными отчетами"
        with patch("services.github_obsidian_sync_service.resolve_chat_model", return_value="fake-model"):
            with patch("services.github_obsidian_sync_service.generate", return_value="- [ ] (P0) Сделать MVP"):
                with patch(
                    "services.github_obsidian_sync_service.upsert_obsidian_note",
                    return_value={"ok": True, "path": "/tmp/Idea.md"},
                ) as upsert_mock:
                    result = analyze_project_idea_to_obsidian(idea=idea, title="Finance MVP")

        self.assertIn("записала план", result.lower())
        kwargs = upsert_mock.call_args.kwargs
        self.assertEqual(kwargs["title"], "Finance MVP")
        self.assertEqual(kwargs["mode"], "replace")
        self.assertIn("Исходная идея", kwargs["content"])
        self.assertIn("План реализации", kwargs["content"])


class ProjectIdeaIntentFastpathTests(unittest.TestCase):
    def test_detect_fast_intent_for_project_idea_to_obsidian(self) -> None:
        text = (
            "Проанализируй идею проекта ассистент для родителей и распиши задачи по реализации в обсидиан"
        )
        intent = detect_fast_intent(text)
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "analyze_project_idea_to_obsidian")
        self.assertIn("ассистент для родителей", intent.data["idea"])

    def test_detect_fast_intent_with_explicit_obsidian_note_title(self) -> None:
        text = (
            "Составь план по идее помощник для изучения языков в заметку Language Coach MVP в обсидиан"
        )
        intent = detect_fast_intent(text)
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "analyze_project_idea_to_obsidian")
        self.assertIn("помощник для изучения языков", intent.data["idea"])
        self.assertEqual(intent.data.get("title"), "Language Coach MVP")

    def test_detect_fast_intent_with_quoted_title(self) -> None:
        text = (
            'Проанализируй идею "планировщик обучения" в заметку "My Learning Plan" в обсидиан'
        )
        intent = detect_fast_intent(text)
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "analyze_project_idea_to_obsidian")
        self.assertEqual(intent.data.get("idea"), "планировщик обучения")
        self.assertEqual(intent.data.get("title"), "My Learning Plan")


if __name__ == "__main__":
    unittest.main()
