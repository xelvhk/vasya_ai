from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from services.project_registry_store import (
    ProjectRegistryFormatError,
    ProjectRegistryStore,
    UserProject,
)


class ProjectRegistryStoreTests(unittest.TestCase):
    def test_missing_registry_starts_empty_without_creating_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "state" / "project_registry.json"
            store = ProjectRegistryStore(registry_path)

            self.assertEqual(store.list(), [])
            self.assertFalse(registry_path.exists())

    def test_add_persists_a_versioned_project_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "state" / "project_registry.json"
            project_path = root / "project"
            store = ProjectRegistryStore(registry_path)

            project = store.add(
                UserProject(
                    id="sample_project",
                    name="Sample Project",
                    path=str(project_path),
                    kind="python",
                    priority=20,
                )
            )

            self.assertEqual(project.id, "sample_project")
            self.assertEqual(ProjectRegistryStore(registry_path).list(), [project])
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], 1)
            self.assertEqual(payload["projects"][0]["path"], str(project_path))

    def test_disabled_projects_are_hidden_unless_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ProjectRegistryStore(root / "registry.json")
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

            self.assertEqual([item.id for item in store.list()], ["active"])
            self.assertEqual(
                [item.id for item in store.list(include_disabled=True)],
                ["active", "paused"],
            )

    def test_update_can_change_values_and_disable_a_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ProjectRegistryStore(root / "registry.json")
            store.add(UserProject("sample", "Sample", str(root / "sample"), "python", 10))

            updated = store.update(
                "sample",
                name="Renamed",
                kind="web",
                priority=30,
                enabled=False,
            )

            self.assertEqual(updated.name, "Renamed")
            self.assertEqual(updated.kind, "web")
            self.assertEqual(updated.priority, 30)
            self.assertFalse(updated.enabled)
            self.assertEqual(store.list(), [])

    def test_remove_deletes_only_the_selected_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ProjectRegistryStore(root / "registry.json")
            store.add(UserProject("one", "One", str(root / "one"), "python", 10))
            store.add(UserProject("two", "Two", str(root / "two"), "web", 20))

            removed = store.remove("one")

            self.assertEqual(removed.id, "one")
            self.assertEqual([item.id for item in store.list()], ["two"])

    def test_rejects_duplicate_ids_and_relative_paths_without_touching_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_path = root / "does-not-need-to-exist"
            store = ProjectRegistryStore(root / "registry.json")
            store.add(UserProject("sample", "Sample", str(project_path), "python", 10))

            with self.assertRaises(ValueError):
                store.add(UserProject("sample", "Other", str(root / "other"), "web", 20))
            with self.assertRaises(ValueError):
                store.add(UserProject("relative", "Relative", "projects/relative", "web", 20))

            self.assertFalse(project_path.exists())
            self.assertEqual([item.id for item in store.list()], ["sample"])

    def test_invalid_or_future_registry_format_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            registry_path.write_text("{not-json", encoding="utf-8")

            with self.assertRaises(ProjectRegistryFormatError):
                ProjectRegistryStore(registry_path).list()

            registry_path.write_text(
                json.dumps({"version": 99, "projects": []}),
                encoding="utf-8",
            )
            with self.assertRaises(ProjectRegistryFormatError):
                ProjectRegistryStore(registry_path).list()

    def test_export_writes_a_portable_registry_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ProjectRegistryStore(root / "registry.json")
            store.add(UserProject("sample", "Sample", str(root / "sample"), "python", 10))
            export_path = root / "backup" / "projects.json"

            store.export(export_path)

            self.assertEqual(
                ProjectRegistryStore(export_path).list(include_disabled=True),
                store.list(include_disabled=True),
            )


if __name__ == "__main__":
    unittest.main()
