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

    def test_control_center_javascript_fetches_project_status(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center/assets/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn('/v1/projects/status', response.text)
        self.assertIn('vasyaApiToken', response.text)

    def test_control_center_rejects_missing_asset(self) -> None:
        with patch("apps.api.main.log_interaction_event"):
            with TestClient(api_main.app) as client:
                response = client.get("/control-center/assets/missing.js")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
