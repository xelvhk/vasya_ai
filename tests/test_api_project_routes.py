from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient

    from apps.api import main as api_main
    from services.project_registry_service import ProjectStatus

    _FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    _FASTAPI_AVAILABLE = False


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi is not installed in the current virtual environment")
class ApiProjectRoutesTests(unittest.TestCase):
    def test_project_status_returns_empty_items_by_default(self) -> None:
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/v1/projects/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": []})

    def test_project_status_returns_service_items(self) -> None:
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
            dirty=False,
            latest_commit="abc1234 Add project status",
            next_action="Review project status.",
        )

        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.routes.projects.list_project_status",
            return_value=[project],
        ), patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/v1/projects/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["items"][0]["id"], "ai_pal")
        self.assertEqual(payload["items"][0]["branch"], "main")
        self.assertFalse(payload["items"][0]["dirty"])


if __name__ == "__main__":
    unittest.main()
