from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from config.projects import (
    PERSONAL_PROJECT_PRESETS,
    ProjectConfig,
    configured_project_configs,
)
from services.project_registry_service import list_project_registry, list_project_status
from services.project_registry_store import ProjectRegistryStore, UserProject


class ProjectRegistryTests(unittest.TestCase):
    def test_default_registry_is_empty_for_installed_users(self) -> None:
        projects = list_project_registry()

        self.assertEqual(projects, [])

    def test_personal_presets_can_represent_active_projects_when_enabled(self) -> None:
        project_ids = {project.id for project in PERSONAL_PROJECT_PRESETS}

        self.assertEqual(
            {
                "ai_pal",
                "portfolio",
                "ai_twin",
                "ai_predictor",
                "document_ops_ai",
                "onboardica",
            },
            project_ids,
        )

    def test_configured_projects_can_include_personal_presets_explicitly(self) -> None:
        projects = configured_project_configs(include_personal_presets=True)

        self.assertEqual(projects, PERSONAL_PROJECT_PRESETS)

    def test_env_flag_can_include_personal_presets(self) -> None:
        with patch.dict("os.environ", {"VASYA_PROJECT_OS_INCLUDE_PERSONAL_DEFAULTS": "true"}):
            projects = configured_project_configs()

        self.assertEqual(projects, PERSONAL_PROJECT_PRESETS)

    def test_default_registry_loads_only_active_user_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "project_registry.json"
            store = ProjectRegistryStore(registry_path)
            store.add(UserProject("active", "Active", str(root / "active"), "python", 10))
            store.add(
                UserProject(
                    "paused",
                    "Paused",
                    str(root / "paused"),
                    "web",
                    20,
                    enabled=False,
                )
            )

            with patch(
                "services.project_registry_service.PROJECT_REGISTRY_FILE",
                str(registry_path),
            ):
                projects = list_project_registry()

        self.assertEqual([project.id for project in projects], ["active"])

    def test_registry_marks_existing_project_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = ProjectConfig(
                id="example",
                name="Example",
                path=root,
                kind="python",
                priority=10,
            )

            projects = list_project_registry([config])

        self.assertEqual(projects[0].status, "OK")
        self.assertTrue(projects[0].exists)
        self.assertIsNone(projects[0].warning)

    def test_registry_marks_missing_project_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing"
            config = ProjectConfig(
                id="missing",
                name="Missing",
                path=missing_path,
                kind="python",
                priority=10,
            )

            projects = list_project_registry([config])

        self.assertEqual(projects[0].status, "WARN")
        self.assertFalse(projects[0].exists)
        self.assertIn("missing", projects[0].warning or "")

    def test_registry_returns_projects_by_priority_then_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configs = [
                ProjectConfig("b", "Beta", root, "python", 20),
                ProjectConfig("a", "Alpha", root, "python", 10),
                ProjectConfig("c", "Charlie", root, "python", 10),
            ]

            projects = list_project_registry(configs)

        self.assertEqual([project.id for project in projects], ["a", "c", "b"])

    def test_project_status_includes_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = ProjectConfig("example", "Example", root, "python", 10)

            with patch("services.project_registry_service._git_output") as git_output:
                git_output.side_effect = [
                    ("main", None),
                    (" M main.py", None),
                    ("abc1234 Initial commit", None),
                ]
                projects = list_project_status([config])

        self.assertEqual(projects[0].status, "OK")
        self.assertEqual(projects[0].branch, "main")
        self.assertTrue(projects[0].dirty)
        self.assertEqual(projects[0].latest_commit, "abc1234 Initial commit")
        self.assertEqual(projects[0].next_action, "Review project status.")

    def test_project_status_reports_missing_path_per_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ProjectConfig("missing", "Missing", Path(tmp) / "missing", "python", 10)

            projects = list_project_status([config])

        self.assertEqual(projects[0].status, "WARN")
        self.assertFalse(projects[0].exists)
        self.assertIsNone(projects[0].branch)
        self.assertIsNone(projects[0].dirty)
        self.assertIsNone(projects[0].latest_commit)
        self.assertIn("missing", projects[0].warning or "")

    def test_project_status_reports_git_errors_per_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = ProjectConfig("example", "Example", root, "python", 10)

            with patch("services.project_registry_service._git_output") as git_output:
                git_output.side_effect = [
                    (None, "not a git repository"),
                    (None, "not a git repository"),
                    (None, "not a git repository"),
                ]
                projects = list_project_status([config])

        self.assertEqual(projects[0].status, "WARN")
        self.assertIn("git metadata unavailable", projects[0].warning or "")
        self.assertIsNone(projects[0].branch)
        self.assertIsNone(projects[0].dirty)
        self.assertIsNone(projects[0].latest_commit)


if __name__ == "__main__":
    unittest.main()
