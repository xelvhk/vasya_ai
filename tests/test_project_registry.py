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
from services.project_registry_service import list_project_registry


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


if __name__ == "__main__":
    unittest.main()
