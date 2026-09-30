from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.main import app
from services.project_registry_service import ProjectStatus


class ProjectChatTests(unittest.TestCase):
    def test_explicit_project_agent_returns_status_with_source(self) -> None:
        project = ProjectStatus(
            id="ai_pal",
            name="Vasya AI",
            path="/projects/ai_pal",
            kind="python_desktop",
            priority=10,
            exists=True,
            status="OK",
            warning=None,
            branch="main",
            dirty=True,
            latest_commit="abc1234 Add project status",
            next_action="Review project status.",
        )
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.routes.chat.list_project_status", return_value=[project], create=True
        ), patch("apps.api.routes.chat.process_text_detailed") as generic_chat, patch(
            "apps.api.main.log_interaction_event"
        ), patch("apps.api.routes.chat.log_interaction_event"):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/chat", json={"text": "Что с проектами?", "agent": "projects"}
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "project_status_summary")
        self.assertIn("Vasya AI", payload["response"])
        self.assertEqual(payload["sources"][0]["id"], "project:ai_pal")
        self.assertEqual(payload["sources"][0]["title"], "Vasya AI")
        self.assertEqual(payload["sources"][0]["url"], "/control-center#project-ai_pal")
        self.assertTrue(payload["sources"][0]["observed_at"])
        generic_chat.assert_not_called()

    def test_empty_project_registry_returns_no_sources(self) -> None:
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.routes.chat.list_project_status", return_value=[], create=True
        ), patch("apps.api.main.log_interaction_event"), patch(
            "apps.api.routes.chat.log_interaction_event"
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/chat", json={"text": "Что с проектами?", "agent": "projects"}
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"], [])
        self.assertTrue(response.json()["needs_followup"])

    def test_unknown_agent_is_rejected(self) -> None:
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.main.log_interaction_event"
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/chat", json={"text": "status", "agent": "unsupported"}
                )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
