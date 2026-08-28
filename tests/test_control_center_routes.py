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
        self.assertIn('href="#main-content"', response.text)
        self.assertLess(
            response.text.index('id="project-grid"'),
            response.text.index('id="project-management"'),
        )
        self.assertNotIn("dashboard-hero", response.text)
        self.assertNotIn("device-frame", response.text)

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
        self.assertIn('id="project-form-error"', response.text)
        self.assertIn('tabindex="-1"', response.text)
        self.assertIn('aria-describedby="project-form-error', response.text)

    def test_control_center_serves_session_scoped_connection_dialog(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                page = client.get("/control-center")
                script = client.get("/control-center/assets/api-client.js")

        self.assertEqual(page.status_code, 200)
        self.assertIn('id="connection-dialog"', page.text)
        self.assertIn('id="open-connection-dialog"', page.text)
        self.assertIn('autocomplete="current-password"', page.text)
        self.assertIn('type="module"', page.text)
        self.assertEqual(script.status_code, 200)
        self.assertIn("sessionStorage", script.text)
        self.assertNotIn("localStorage", script.text)

    def test_control_center_javascript_fetches_project_status(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center/assets/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn('/v1/projects/status', response.text)
        self.assertIn('createApiClient', response.text)

    def test_control_center_javascript_manages_project_registry(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center/assets/app.js")
                project_actions = client.get(
                    "/control-center/assets/project-actions.js"
                )
                api_client = client.get("/control-center/assets/api-client.js")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(project_actions.status_code, 200)
        self.assertIn('"/v1/projects"', project_actions.text)
        self.assertIn('"POST"', project_actions.text)
        self.assertIn('"PATCH"', project_actions.text)
        self.assertIn('method: "DELETE"', project_actions.text)
        self.assertIn("showModal()", project_actions.text)
        self.assertEqual(api_client.status_code, 200)
        self.assertIn("responsePayload.detail", api_client.text)
        self.assertNotIn(
            "insertAdjacentHTML",
            response.text + project_actions.text,
        )

    def test_control_center_rejects_missing_asset(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center/assets/missing.js")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
