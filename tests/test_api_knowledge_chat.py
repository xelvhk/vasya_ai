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
            with patch.dict(os.environ, {"VASYA_KNOWLEDGE_VAULT_PATH": str(vault)}), patch(
                "apps.api.deps.VASYA_API_REQUIRE_AUTH", False
            ), patch("apps.api.main.log_interaction_event"), patch(
                "apps.api.routes.chat.log_interaction_event"
            ):
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/chat",
                        json={"text": "Где хранится локальный контекст?", "agent": "knowledge"},
                    )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "knowledge_search")
        self.assertIn("домашнем хранилище", payload["response"])
        self.assertNotIn("секретный пароль", payload["response"])
        self.assertEqual(payload["sources"][0]["id"], "obsidian:30_Knowledge/Context.md")
        self.assertTrue(payload["sources"][0]["observed_at"])

    def test_no_match_does_not_invent_answer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            (vault / "10_Projects" / "Active").mkdir(parents=True)
            with patch.dict(os.environ, {"VASYA_KNOWLEDGE_VAULT_PATH": str(vault)}), patch(
                "apps.api.deps.VASYA_API_REQUIRE_AUTH", False
            ), patch("apps.api.main.log_interaction_event"), patch(
                "apps.api.routes.chat.log_interaction_event"
            ):
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/chat",
                        json={"text": "Какая выручка?", "agent": "knowledge"},
                    )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"], [])
        self.assertTrue(response.json()["needs_followup"])


if __name__ == "__main__":
    unittest.main()
