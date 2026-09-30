from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import Mock, patch

from services.allowed_knowledge_service import KnowledgeHit
from services.grounded_knowledge_answer_service import answer_from_hits
from services.ollama_client import OllamaClientError


class GroundedKnowledgeAnswerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hits = (
            KnowledgeHit(
                "30_Knowledge/Context.md", "Context",
                "Локальный контекст хранится на домашнем сервере.",
                "obsidian://open?vault=Test&file=30_Knowledge%2FContext.md",
                datetime.now(timezone.utc),
            ),
        )

    @patch("services.grounded_knowledge_answer_service.resolve_chat_model", return_value="local-test")
    @patch("services.grounded_knowledge_answer_service.generate")
    def test_valid_answer_has_server_generated_citation(self, generate: Mock, _model: Mock) -> None:
        generate.return_value = (
            '{"answer":"Контекст хранится на домашнем сервере.",'
            '"source":1,"quote":"Локальный контекст хранится на домашнем сервере."}'
        )
        result = answer_from_hits("Где контекст?", self.hits)
        self.assertEqual(result, "Контекст хранится на домашнем сервере. [1]\nОснование: «Локальный контекст хранится на домашнем сервере.»")
        kwargs = generate.call_args.kwargs
        self.assertEqual(kwargs["model"], "local-test")
        self.assertEqual(kwargs["temperature"], 0)
        self.assertIn("Где контекст?", generate.call_args.args[0])
        self.assertIn(self.hits[0].excerpt, generate.call_args.args[0])
        self.assertNotIn("obsidian://", generate.call_args.args[0])

    @patch("services.grounded_knowledge_answer_service.resolve_chat_model", return_value="local-test")
    @patch("services.grounded_knowledge_answer_service.generate")
    def test_fabricated_quote_or_source_is_rejected(self, generate: Mock, _model: Mock) -> None:
        generate.return_value = '{"answer":"На облачном сервере.","source":1,"quote":"В облаке."}'
        self.assertIsNone(answer_from_hits("Где контекст?", self.hits))
        generate.return_value = '{"answer":"На сервере.","source":2,"quote":"Локальный контекст"}'
        self.assertIsNone(answer_from_hits("Где контекст?", self.hits))

    @patch("services.grounded_knowledge_answer_service.resolve_chat_model", return_value="local-test")
    @patch("services.grounded_knowledge_answer_service.generate")
    def test_malformed_or_unavailable_model_falls_back(self, generate: Mock, _model: Mock) -> None:
        generate.return_value = "Контекст в облаке [1]"
        self.assertIsNone(answer_from_hits("Где контекст?", self.hits))
        generate.side_effect = OllamaClientError("offline")
        self.assertIsNone(answer_from_hits("Где контекст?", self.hits))


if __name__ == "__main__":
    unittest.main()
