from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient

    from apps.api import main as api_main
    from config.settings import APP_VERSION

    _FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    _FASTAPI_AVAILABLE = False


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi is not installed in the current virtual environment")
class ApiHealthRoutesTests(unittest.TestCase):
    def test_openapi_version_matches_app_version(self) -> None:
        with TestClient(api_main.app) as client:
            response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["info"]["version"], APP_VERSION)

    def test_health_live_returns_ok(self) -> None:
        with TestClient(api_main.app) as client:
            response = client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "ok")

    def test_health_ready_reports_ready_when_checks_pass(self) -> None:
        with patch("apps.api.routes.system.VASYA_API_REQUIRE_AUTH", True), patch(
            "apps.api.routes.system.VASYA_API_AUTH_TOKEN",
            "token",
        ), patch("apps.api.routes.system.TASKS_BACKEND", "obsidian_daily"), patch(
            "apps.api.routes.system.resolve_obsidian_vault_path",
            return_value=(object(), None),
        ):
            with TestClient(api_main.app) as client:
                response = client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("status"), "ready")
        self.assertTrue(payload.get("ready"))

    def test_health_ready_reports_not_ready_when_obsidian_missing(self) -> None:
        with patch("apps.api.routes.system.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.routes.system.TASKS_BACKEND",
            "obsidian_daily",
        ), patch(
            "apps.api.routes.system.resolve_obsidian_vault_path",
            return_value=(None, "vault missing"),
        ):
            with TestClient(api_main.app) as client:
                response = client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("status"), "not_ready")
        self.assertFalse(payload.get("ready"))
        self.assertIn("vault", str(payload.get("checks", {}).get("obsidian_vault", {}).get("error", "")).lower())


if __name__ == "__main__":
    unittest.main()
