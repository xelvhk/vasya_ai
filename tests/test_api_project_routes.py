from __future__ import annotations

from pathlib import Path
import tempfile
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
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.routes.projects.list_project_status", return_value=[]
        ), patch("apps.api.main.log_interaction_event"):
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

    def test_registry_crud_round_trip_includes_disabled_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "state" / "project_registry.json"
            project_path = root / "sample-project"
            with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
                "apps.api.routes.projects.PROJECT_REGISTRY_FILE",
                str(registry_path),
            ), patch("apps.api.main.log_interaction_event"):
                with TestClient(api_main.app) as client:
                    create_response = client.post(
                        "/v1/projects",
                        json={
                            "id": "sample",
                            "name": "Sample Project",
                            "path": str(project_path),
                            "kind": "python",
                            "priority": 10,
                        },
                    )
                    list_response = client.get("/v1/projects")
                    update_response = client.patch(
                        "/v1/projects/sample",
                        json={"name": "Renamed Project", "enabled": False},
                    )
                    disabled_list_response = client.get("/v1/projects")
                    delete_response = client.delete("/v1/projects/sample")
                    empty_list_response = client.get("/v1/projects")

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(
            create_response.json(),
            {
                "id": "sample",
                "name": "Sample Project",
                "path": str(project_path),
                "kind": "python",
                "priority": 10,
                "enabled": True,
            },
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([item["id"] for item in list_response.json()["items"]], ["sample"])
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["name"], "Renamed Project")
        self.assertFalse(update_response.json()["enabled"])
        self.assertFalse(disabled_list_response.json()["items"][0]["enabled"])
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(empty_list_response.json(), {"items": []})
        self.assertFalse(project_path.exists())

    def test_registry_create_reports_duplicate_and_invalid_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "project_registry.json"
            valid_payload = {
                "id": "sample",
                "name": "Sample",
                "path": str(root / "sample"),
                "kind": "python",
                "priority": 10,
            }
            with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
                "apps.api.routes.projects.PROJECT_REGISTRY_FILE",
                str(registry_path),
            ), patch("apps.api.main.log_interaction_event"):
                with TestClient(api_main.app) as client:
                    first_response = client.post("/v1/projects", json=valid_payload)
                    duplicate_response = client.post("/v1/projects", json=valid_payload)
                    invalid_response = client.post(
                        "/v1/projects",
                        json={**valid_payload, "id": "relative", "path": "projects/sample"},
                    )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(duplicate_response.status_code, 409)
        self.assertEqual(duplicate_response.json()["detail"], "Project id already exists.")
        self.assertEqual(invalid_response.status_code, 422)
        self.assertEqual(invalid_response.json()["detail"], "Project path must be absolute.")

    def test_registry_update_and_delete_report_unknown_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "project_registry.json"
            with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
                "apps.api.routes.projects.PROJECT_REGISTRY_FILE",
                str(registry_path),
            ), patch("apps.api.main.log_interaction_event"):
                with TestClient(api_main.app) as client:
                    update_response = client.patch(
                        "/v1/projects/missing",
                        json={"enabled": False},
                    )
                    delete_response = client.delete("/v1/projects/missing")

        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(update_response.json()["detail"], "Project not found.")
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(delete_response.json()["detail"], "Project not found.")

    def test_registry_rejects_empty_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "project_registry.json"
            with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
                "apps.api.routes.projects.PROJECT_REGISTRY_FILE",
                str(registry_path),
            ), patch("apps.api.main.log_interaction_event"):
                with TestClient(api_main.app) as client:
                    response = client.patch("/v1/projects/sample", json={})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "At least one project field is required.")

    def test_registry_format_errors_do_not_expose_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "project_registry.json"
            registry_path.write_text('{"private": "do-not-return"', encoding="utf-8")
            with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
                "apps.api.routes.projects.PROJECT_REGISTRY_FILE",
                str(registry_path),
            ), patch("apps.api.main.log_interaction_event"):
                with TestClient(api_main.app) as client:
                    response = client.get("/v1/projects")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Project registry could not be read safely.")
        self.assertNotIn("do-not-return", response.text)

    def test_registry_mutations_require_the_configured_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "project_registry.json"
            payload = {
                "id": "sample",
                "name": "Sample",
                "path": str(root / "sample"),
                "kind": "python",
                "priority": 10,
            }
            with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", True), patch(
                "apps.api.deps.VASYA_API_AUTH_TOKEN",
                "test-api-key",
            ), patch(
                "apps.api.routes.projects.PROJECT_REGISTRY_FILE",
                str(registry_path),
            ), patch("apps.api.main.log_interaction_event"):
                with TestClient(api_main.app) as client:
                    unauthorized_response = client.post("/v1/projects", json=payload)
                    authorized_response = client.post(
                        "/v1/projects",
                        json=payload,
                        headers={"X-API-Key": "test-api-key"},
                    )

        self.assertEqual(unauthorized_response.status_code, 401)
        self.assertEqual(
            unauthorized_response.json()["detail"],
            "Invalid or missing API key.",
        )
        self.assertEqual(authorized_response.status_code, 201)


if __name__ == "__main__":
    unittest.main()
