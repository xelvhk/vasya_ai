from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from services.memory_center_service import MemoryCenterService
from services.memory_sync_service import (
    sync_memory_source,
    sync_github_to_memory,
    sync_notion_to_memory,
    sync_obsidian_to_memory,
)


class MemorySyncServiceTests(unittest.TestCase):
    def test_sync_github_ingests_commits_and_pull_requests(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vasya.db"
            wiki_dir = Path(tmp) / "memory_wiki"

            with patch("storage.db.STORAGE_DB_FILE", str(db_path)), patch(
                "services.memory_center_service.MEMORY_WIKI_DIR",
                str(wiki_dir),
            ), patch(
                "services.memory_sync_service.fetch_recent_commits",
                return_value=[
                    {
                        "sha": "abc1234",
                        "message": "Add memory center",
                        "author": "Example User",
                        "date": "2026-05-14T10:00:00Z",
                        "url": "https://github.com/example/repo/commit/abc1234",
                    }
                ],
            ), patch(
                "services.memory_sync_service.fetch_recent_pull_requests",
                return_value=[
                    {
                        "number": 7,
                        "title": "Memory status API",
                        "state": "open",
                        "updated_at": "2026-05-14T11:00:00Z",
                        "url": "https://github.com/example/repo/pull/7",
                    }
                ],
            ), patch("services.memory_sync_service.now_utc_iso", return_value="2026-05-14T12:00:00+00:00"):
                result = sync_github_to_memory(repo="example/repo", force=True)
                status = MemoryCenterService(wiki_dir=wiki_dir).get_status()

            self.assertTrue(result["ok"])
            self.assertEqual(result["ingested"], 2)
            self.assertEqual(status["chunks_count"], 2)
            self.assertEqual(status["sources"][0]["source_key"], "github_example_repo")

    def test_sync_obsidian_ingests_markdown_notes_from_vault(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vasya.db"
            wiki_dir = Path(tmp) / "memory_wiki"
            vault = Path(tmp) / "Vault"
            note = vault / "03_Knowledge" / "Vasya.md"
            note.parent.mkdir(parents=True)
            note.write_text(
                """---
type: knowledge
tags:
  - vasya
---
# Vasya

Memory Center should stay local-first.
""",
                encoding="utf-8",
            )

            with patch("storage.db.STORAGE_DB_FILE", str(db_path)), patch(
                "services.memory_center_service.MEMORY_WIKI_DIR",
                str(wiki_dir),
            ), patch(
                "services.memory_sync_service.resolve_obsidian_vault_path",
                return_value=(vault, None),
            ):
                result = sync_obsidian_to_memory(force=True)
                status = MemoryCenterService(wiki_dir=wiki_dir).get_status()

            self.assertTrue(result["ok"])
            self.assertEqual(result["ingested"], 1)
            self.assertEqual(status["chunks_count"], 1)
            self.assertIn("obsidian", status["sources"][0]["source_key"])

    def test_sync_notion_ingests_page_snapshot(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vasya.db"
            wiki_dir = Path(tmp) / "memory_wiki"

            with patch("storage.db.STORAGE_DB_FILE", str(db_path)), patch(
                "services.memory_center_service.MEMORY_WIKI_DIR",
                str(wiki_dir),
            ), patch(
                "services.memory_sync_service.read_page_text",
                return_value=["Decision: keep local-first memory.", "Next: add desktop status."],
            ), patch("services.memory_sync_service.now_utc_iso", return_value="2026-05-14T12:00:00+00:00"):
                result = sync_notion_to_memory(page_id="page-123", force=True)
                status = MemoryCenterService(wiki_dir=wiki_dir).get_status()

            self.assertTrue(result["ok"])
            self.assertEqual(result["ingested"], 1)
            self.assertEqual(status["chunks_count"], 1)
            self.assertIn("notion", status["sources"][0]["source_key"])

    def test_sync_all_is_ok_when_at_least_one_source_succeeds(self) -> None:
        with patch(
            "services.memory_sync_service.sync_github_to_memory",
            return_value={"ok": False, "source": "github", "error": "not configured"},
        ), patch(
            "services.memory_sync_service.sync_notion_to_memory",
            return_value={"ok": False, "source": "notion", "error": "not configured"},
        ), patch(
            "services.memory_sync_service.sync_obsidian_to_memory",
            return_value={"ok": True, "source": "obsidian", "ingested": 2},
        ):
            result = sync_memory_source("all", force=True)

        self.assertTrue(result["ok"])
        self.assertEqual(result["ingested"], 2)
        self.assertEqual(result["successful_sources"], ["obsidian"])
        self.assertEqual(len(result["errors"]), 2)


if __name__ == "__main__":
    unittest.main()
