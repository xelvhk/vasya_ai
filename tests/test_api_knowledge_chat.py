from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.main import app


class KnowledgeChatTests(unittest.TestCase):
    def test_knowledge_agent_returns_allowed_excerpt_with_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            allowed = vault / "30_Knowledge"
            allowed.mkdir()
            (allowed / "Context.md").write_text(
                "# Context\nЛокальный контекст хранится в домашнем хранилище.\n",
                encoding="utf-8",
            )
            private = vault / "20_Areas" / "Personal"
            private.mkdir(parents=True)
            (private / "Secret.md").write_text(
                "Локальный контекст содержит секретный пароль.\n", encoding="utf-8"
            )
            with patch.dict(os.environ, {
                "VASYA_KNOWLEDGE_VAULT_PATH": str(vault),
                "VASYA_KNOWLEDGE_INDEX_FILE": str(vault / "knowledge.db"),
            }), patch(
                "apps.api.deps.VASYA_API_REQUIRE_AUTH", False
            ), patch("apps.api.main.log_interaction_event"), patch(
                "apps.api.routes.chat.log_interaction_event"
            ), patch(
                "apps.api.routes.chat.answer_from_hits", return_value=None
            ):
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/chat",
                        json={"text": "Где хранится локальный контекст?", "agent": "knowledge"},
                    )
                index_created = (vault / "knowledge.db").is_file()

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "knowledge_search")
        self.assertIn("домашнем хранилище", payload["response"])
        self.assertNotIn("секретный пароль", payload["response"])
        self.assertEqual(payload["sources"][0]["id"], "obsidian:30_Knowledge/Context.md")
        self.assertTrue(payload["sources"][0]["observed_at"])
        self.assertTrue(index_created)

    def test_knowledge_agent_returns_grounded_answer_with_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            allowed = vault / "30_Knowledge"
            allowed.mkdir()
            (allowed / "Context.md").write_text(
                "# Context\nЛокальный контекст хранится на домашнем сервере.\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {
                "VASYA_KNOWLEDGE_VAULT_PATH": str(vault),
                "VASYA_KNOWLEDGE_INDEX_FILE": str(vault / "knowledge.db"),
            }), patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
                "apps.api.main.log_interaction_event"
            ), patch("apps.api.routes.chat.log_interaction_event"), patch(
                "apps.api.routes.chat.answer_from_hits",
                return_value="Контекст хранится на домашнем сервере. [1]",
            ) as answer:
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/chat",
                        json={"text": "Где контекст?", "agent": "knowledge"},
                    )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "knowledge_answer")
        self.assertIn("домашнем сервере. [1]", response.json()["response"])
        self.assertEqual(response.json()["sources"][0]["id"], "obsidian:30_Knowledge/Context.md")
        self.assertEqual(answer.call_count, 1)

    def test_no_match_does_not_invent_answer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            (vault / "10_Projects" / "Active").mkdir(parents=True)
            with patch.dict(os.environ, {
                "VASYA_KNOWLEDGE_VAULT_PATH": str(vault),
                "VASYA_KNOWLEDGE_INDEX_FILE": str(vault / "knowledge.db"),
            }), patch(
                "apps.api.deps.VASYA_API_REQUIRE_AUTH", False
            ), patch("apps.api.main.log_interaction_event"), patch(
                "apps.api.routes.chat.log_interaction_event"
            ), patch(
                "apps.api.routes.chat.answer_from_hits"
            ) as answer:
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/chat",
                        json={"text": "Какая выручка?", "agent": "knowledge"},
                    )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"], [])
        self.assertTrue(response.json()["needs_followup"])
        answer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
