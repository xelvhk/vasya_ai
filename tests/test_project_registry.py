from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from config.projects import ProjectConfig
from services.project_registry_service import list_project_registry


class ProjectRegistryTests(unittest.TestCase):
    def test_default_registry_contains_active_projects(self) -> None:
        projects = list_project_registry()
        project_ids = {project.id for project in projects}

        self.assertIn("ai_pal", project_ids)
        self.assertIn("portfolio", project_ids)
        self.assertIn("ai_twin", project_ids)
        self.assertIn("ai_predictor", project_ids)
        self.assertIn("document_ops_ai", project_ids)
        self.assertIn("onboardica", project_ids)

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
