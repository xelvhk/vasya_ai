from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import obsidian_daily_tasks_service as daily


class ObsidianDailyTasksTests(unittest.TestCase):
    def test_create_and_list_tasks_in_daily_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "Daily").mkdir(parents=True, exist_ok=True)
            with patch(
                "services.obsidian_daily_tasks_service.resolve_obsidian_vault_path",
                return_value=(vault, None),
            ):
                created = daily.create_task_in_daily_note("Позвонить клиенту")
                self.assertEqual(created.get("source"), "obsidian_daily")
                items = daily.list_tasks_from_daily_notes()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["task"], "Позвонить клиенту")

    def test_complete_and_delete_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "Daily").mkdir(parents=True, exist_ok=True)
            with patch(
                "services.obsidian_daily_tasks_service.resolve_obsidian_vault_path",
                return_value=(vault, None),
            ):
                _ = daily.create_task_in_daily_note("Подготовить отчет")
                items = daily.list_tasks_from_daily_notes()
                target_id = str(items[0]["id"])
                completed = daily.complete_task_in_daily_notes(target=target_id)
                self.assertIsNotNone(completed)
                remaining = daily.list_tasks_from_daily_notes()
                self.assertEqual(len(remaining), 0)
                deleted = daily.delete_task_from_daily_notes(target=target_id)
                self.assertFalse(deleted)

    def test_prefers_existing_daily_folder_from_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "Ежедневные").mkdir(parents=True, exist_ok=True)
            with patch(
                "services.obsidian_daily_tasks_service.resolve_obsidian_vault_path",
                return_value=(vault, None),
            ):
                with patch(
                    "services.obsidian_daily_tasks_service.OBSIDIAN_DAILY_NOTES_DIRS",
                    ["Daily", "Ежедневные"],
                ):
                    path = daily._daily_note_path("2026-04-28")
        self.assertIsNotNone(path)
        assert path is not None
        self.assertIn("Ежедневные", str(path))

    def test_prioritizes_day_plan_section_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            daily_dir = vault / "Daily"
            daily_dir.mkdir(parents=True, exist_ok=True)
            note_path = daily_dir / "2026-04-29.md"
            note_path.write_text(
                (
                    "# 2026-04-29\n\n"
                    "## Задачи\n"
                    "- [ ] Третья задача\n\n"
                    "## План на день\n"
                    "- [ ] Первая задача\n"
                    "- [ ] Вторая задача\n"
                ),
                encoding="utf-8",
            )
            with patch(
                "services.obsidian_daily_tasks_service.resolve_obsidian_vault_path",
                return_value=(vault, None),
            ):
                items = daily.list_tasks_from_daily_notes(filter_date="2026-04-29")

        self.assertEqual([item["task"] for item in items], ["Первая задача", "Вторая задача", "Третья задача"])


if __name__ == "__main__":
    unittest.main()
