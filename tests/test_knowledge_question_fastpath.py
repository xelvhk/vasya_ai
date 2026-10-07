from __future__ import annotations

import unittest
from unittest.mock import patch

from core.intent_parser import parse_intent
from services.chat_service import _build_memory_context


class KnowledgeQuestionFastpathTests(unittest.TestCase):
    def test_conceptual_questions_skip_the_intent_model(self) -> None:
        for question in (
            "Как работает планировщик задач?",
            "Почему встречи иногда переносятся",
            "Объясни, что такое календарь событий",
        ):
            with self.subTest(question=question):
                with patch("core.intent_parser.generate", side_effect=AssertionError("intent model called")):
                    self.assertEqual(parse_intent(question).intent, "chat")

    def test_personal_and_action_requests_still_use_intent_routing(self) -> None:
        for question in (
            "Объясни, какие у меня встречи завтра",
            "Как устроены задачи, и удали все задачи",
            "Почему в памяти нет записи о совещании?",
            "Объясни, что означает эта заметка",
            "Расскажи про задачи",
        ):
            with self.subTest(question=question):
                with (
                    patch("core.intent_parser.generate", return_value='{"intent":"chat","data":{}}') as generate,
                    patch("core.intent_parser.log_voice_event"),
                ):
                    self.assertEqual(parse_intent(question).intent, "chat")
                generate.assert_called_once()

    def test_conceptual_question_does_not_search_personal_memory(self) -> None:
        with (
            patch("services.chat_service.search_memory") as search_memory,
            patch("services.chat_service.get_memory_snapshot") as get_memory_snapshot,
        ):
            self.assertIsNone(_build_memory_context("Как работает планировщик задач?"))
        search_memory.assert_not_called()
        get_memory_snapshot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
