from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from services.memory_center_service import (
    MemoryCenterService,
    MemorySyncPlanner,
    build_memory_center_summary,
)


class MemoryCenterServiceTests(unittest.TestCase):
    def test_ingest_text_creates_source_chunk_and_markdown_artifact(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vasya.db"
            wiki_dir = Path(tmp) / "memory_wiki"

            with patch("storage.db.STORAGE_DB_FILE", str(db_path)):
                service = MemoryCenterService(wiki_dir=wiki_dir)
                chunk = service.ingest_text(
                    source_key="github",
                    source_name="GitHub",
                    title="Open PR review",
                    content="PR #42 added the Memory Center status endpoint.",
                    external_id="pr-42",
                    url="https://github.com/example/repo/pull/42",
                    tags=("github", "review"),
                )

                status = service.get_status()

            self.assertEqual(status["sources_count"], 1)
            self.assertEqual(status["chunks_count"], 1)
            self.assertEqual(status["latest_chunk"]["title"], "Open PR review")
            self.assertTrue(Path(chunk.markdown_path).exists())

            markdown = Path(chunk.markdown_path).read_text(encoding="utf-8")
            self.assertIn("source_key: github", markdown)
            self.assertIn("external_id: pr-42", markdown)
            self.assertIn("PR #42 added the Memory Center status endpoint.", markdown)

    def test_ingest_text_is_idempotent_for_same_source_and_external_id(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vasya.db"

            with patch("storage.db.STORAGE_DB_FILE", str(db_path)):
                service = MemoryCenterService(wiki_dir=Path(tmp) / "memory_wiki")
                first = service.ingest_text(
                    source_key="notion",
                    source_name="Notion",
                    title="Decision",
                    content="Keep the local-first architecture.",
                    external_id="page-1",
                )
                second = service.ingest_text(
                    source_key="notion",
                    source_name="Notion",
                    title="Decision updated",
                    content="Keep the local-first architecture.",
                    external_id="page-1",
                )
                status = service.get_status()

            self.assertEqual(first.id, second.id)
            self.assertEqual(status["chunks_count"], 1)
            self.assertEqual(status["sources"][0]["chunks_count"], 1)

    def test_sync_planner_tracks_due_state_and_success(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vasya.db"

            with patch("storage.db.STORAGE_DB_FILE", str(db_path)):
                planner = MemorySyncPlanner(default_interval_seconds=1200)
                first_decision = planner.should_sync("github", "default", now_ts=1_000)
                planner.record_success(
                    "github",
                    "default",
                    cursor="cursor-1",
                    synced_at_ts=1_000,
                    items_count=3,
                )
                too_soon = planner.should_sync("github", "default", now_ts=1_500)
                later = planner.should_sync("github", "default", now_ts=2_300)
                status = MemoryCenterService(wiki_dir=Path(tmp) / "memory_wiki").get_status()

            self.assertTrue(first_decision.due)
            self.assertFalse(too_soon.due)
            self.assertEqual(too_soon.next_sync_at_ts, 2_200)
            self.assertTrue(later.due)
            self.assertEqual(status["sync_connections_count"], 1)
            self.assertEqual(status["sync_connections"][0]["last_items_count"], 3)

    def test_search_returns_matching_chunks_with_snippets(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vasya.db"
            wiki_dir = Path(tmp) / "memory_wiki"

            with patch("storage.db.STORAGE_DB_FILE", str(db_path)):
                service = MemoryCenterService(wiki_dir=wiki_dir)
                service.ingest_text(
                    source_key="obsidian",
                    source_name="Obsidian",
                    title="Architecture decision",
                    content="Vasya should keep Memory Center local-first and inspectable.",
                    external_id="adr-1",
                    tags=("architecture",),
                )
                service.ingest_text(
                    source_key="github",
                    source_name="GitHub",
                    title="Unrelated commit",
                    content="Update README screenshots.",
                    external_id="commit-1",
                    tags=("github",),
                )
                result = service.search("inspectable", limit=5)

            self.assertEqual(result["count"], 1)
            item = result["items"][0]
            self.assertEqual(item["title"], "Architecture decision")
            self.assertIn("inspectable", item["snippet"])
            self.assertTrue(Path(item["markdown_path"]).exists())

    def test_build_memory_center_summary_is_human_readable(self) -> None:
        status = {
            "status": "ready",
            "sources_count": 2,
            "chunks_count": 7,
            "sources": [
                {"name": "GitHub vasya_ai", "chunks_count": 4, "last_ingested_at": "2026-05-14 12:00:00"},
                {"name": "Obsidian vault", "chunks_count": 3, "last_ingested_at": "2026-05-14 12:05:00"},
            ],
            "sync_connections": [
                {
                    "toolkit": "github",
                    "connection_id": "owner/repo",
                    "last_items_count": 4,
                    "last_error": None,
                }
            ],
            "latest_chunk": {"title": "PR #7: Memory status API"},
        }

        summary = build_memory_center_summary(status)

        self.assertIn("Sources: 2", summary)
        self.assertIn("Chunks: 7", summary)
        self.assertIn("GitHub vasya_ai", summary)
        self.assertIn("PR #7", summary)


if __name__ == "__main__":
    unittest.main()
