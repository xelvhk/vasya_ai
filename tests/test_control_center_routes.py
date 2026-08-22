from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient

    from apps.api import main as api_main

    _FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    _FASTAPI_AVAILABLE = False


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi is not installed in the current virtual environment")
class ControlCenterRoutesTests(unittest.TestCase):
    def test_control_center_serves_dashboard_shell(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Vasya Project OS", response.text)
        self.assertIn("project-grid", response.text)

    def test_control_center_serves_project_management_controls(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center")

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="project-management"', response.text)
        self.assertIn('id="registry-list"', response.text)
        self.assertIn('id="add-project"', response.text)
        self.assertIn('id="project-dialog"', response.text)
        self.assertIn('id="project-form"', response.text)
        self.assertIn('id="delete-project-dialog"', response.text)
        self.assertIn('aria-live="polite"', response.text)
        self.assertIn('<label for="project-name">', response.text)
        self.assertIn('<label for="project-path">', response.text)

    def test_control_center_javascript_fetches_project_status(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center/assets/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn('/v1/projects/status', response.text)
        self.assertIn('vasyaApiToken', response.text)

    def test_control_center_javascript_manages_project_registry(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center/assets/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn('"/v1/projects"', response.text)
        self.assertIn('"POST"', response.text)
        self.assertIn('"PATCH"', response.text)
        self.assertIn('method: "DELETE"', response.text)
        self.assertIn("showModal()", response.text)
        self.assertIn("responsePayload.detail", response.text)
        self.assertNotIn("insertAdjacentHTML", response.text)

    def test_control_center_rejects_missing_asset(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center/assets/missing.js")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
