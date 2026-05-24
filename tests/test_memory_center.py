from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from services.memory_center_service import (
    MemoryCenterService,
    MemorySyncPlanner,
    build_memory_center_summary,
    build_memory_digest_history_summary,
    build_memory_digest_summary,
    build_memory_recent_summary,
    build_memory_search_summary,
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

    def test_list_recent_returns_latest_chunks_first(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vasya.db"
            wiki_dir = Path(tmp) / "memory_wiki"

            with patch("storage.db.STORAGE_DB_FILE", str(db_path)):
                service = MemoryCenterService(wiki_dir=wiki_dir)
                service.ingest_text(
                    source_key="github",
                    source_name="GitHub",
                    title="Older memory",
                    content="Older content.",
                    external_id="older",
                )
                service.ingest_text(
                    source_key="obsidian",
                    source_name="Obsidian",
                    title="Newer memory",
                    content="Newer content.",
                    external_id="newer",
                )
                result = service.list_recent(limit=2)

            self.assertEqual(result["count"], 2)
            self.assertEqual(result["items"][0]["title"], "Newer memory")
            self.assertEqual(result["items"][1]["title"], "Older memory")

    def test_build_daily_digest_writes_markdown_summary(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vasya.db"
            wiki_dir = Path(tmp) / "memory_wiki"

            with patch("storage.db.STORAGE_DB_FILE", str(db_path)), patch(
                "services.memory_center_service.current_timestamp",
                return_value="2026-05-15 10:00:00",
            ):
                service = MemoryCenterService(wiki_dir=wiki_dir)
                service.ingest_text(
                    source_key="github",
                    source_name="GitHub",
                    title="Merged PR",
                    content="Merged Memory Center pull request.",
                    external_id="pr-1",
                )
                result = service.build_daily_digest(date_text="2026-05-15")

            self.assertTrue(result["ok"])
            self.assertEqual(result["count"], 1)
            digest_path = Path(result["path"])
            self.assertTrue(digest_path.exists())
            digest = digest_path.read_text(encoding="utf-8")
            self.assertIn("# Memory Digest 2026-05-15", digest)
            self.assertIn("Merged PR", digest)

    def test_list_daily_digests_returns_latest_files(self) -> None:
        with TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "memory_wiki"
            digests_dir = wiki_dir / "digests"
            digests_dir.mkdir(parents=True, exist_ok=True)
            (digests_dir / "2026-05-14.md").write_text("Chunks: 1\n", encoding="utf-8")
            (digests_dir / "2026-05-15.md").write_text("Chunks: 3\n", encoding="utf-8")

            service = MemoryCenterService(wiki_dir=wiki_dir)
            result = service.list_daily_digests(limit=5)

        self.assertEqual(result["count"], 2)
        self.assertEqual(result["items"][0]["date"], "2026-05-15")
        self.assertEqual(result["items"][0]["chunks_count"], 3)
        self.assertEqual(result["items"][1]["date"], "2026-05-14")

    def test_list_daily_digests_filters_by_date_range(self) -> None:
        with TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "memory_wiki"
            digests_dir = wiki_dir / "digests"
            digests_dir.mkdir(parents=True, exist_ok=True)
            (digests_dir / "2026-05-14.md").write_text("Chunks: 1\n", encoding="utf-8")
            (digests_dir / "2026-05-15.md").write_text("Chunks: 2\n", encoding="utf-8")
            (digests_dir / "2026-05-16.md").write_text("Chunks: 3\n", encoding="utf-8")

            service = MemoryCenterService(wiki_dir=wiki_dir)
            result = service.list_daily_digests(
                limit=10,
                date_from="2026-05-15",
                date_to="2026-05-16",
            )

        self.assertEqual(result["count"], 2)
        self.assertEqual(result["items"][0]["date"], "2026-05-16")
        self.assertEqual(result["items"][1]["date"], "2026-05-15")

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

    def test_build_memory_search_summary_is_human_readable(self) -> None:
        result = {
            "query": "memory",
            "count": 1,
            "items": [
                {
                    "title": "Memory Search",
                    "source_key": "github",
                    "snippet": "Search should return memory provenance links.",
                    "markdown_path": "/tmp/memory.md",
                    "url": "https://github.com/example/repo",
                }
            ],
        }

        summary = build_memory_search_summary(result)

        self.assertIn("Results: 1", summary)
        self.assertIn("[github] Memory Search", summary)
        self.assertIn("/tmp/memory.md", summary)
        self.assertNotIn("Source:", summary)
        self.assertNotIn("Snippet:", summary)

    def test_build_memory_search_summary_truncates_long_snippet(self) -> None:
        result = {
            "query": "memory",
            "count": 1,
            "items": [
                {
                    "title": "Long snippet",
                    "source_key": "obsidian",
                    "snippet": "x" * 240,
                    "markdown_path": "/tmp/long.md",
                }
            ],
        }

        summary = build_memory_search_summary(result)

        self.assertIn("[obsidian] Long snippet", summary)
        self.assertIn("...", summary)

    def test_build_memory_recent_summary_is_human_readable(self) -> None:
        result = {
            "count": 1,
            "items": [
                {
                    "title": "New memory",
                    "source_key": "obsidian",
                    "snippet": "Fresh memory snippet.",
                    "markdown_path": "/tmp/new.md",
                }
            ],
        }

        summary = build_memory_recent_summary(result)

        self.assertIn("Recent: 1", summary)
        self.assertIn("New memory", summary)
        self.assertIn("/tmp/new.md", summary)

    def test_build_memory_digest_summary_is_human_readable(self) -> None:
        result = {
            "ok": True,
            "date": "2026-05-15",
            "count": 2,
            "path": "/tmp/digest.md",
        }

        summary = build_memory_digest_summary(result)

        self.assertIn("Memory digest 2026-05-15", summary)
        self.assertIn("2 chunks", summary)
        self.assertIn("/tmp/digest.md", summary)

    def test_build_memory_digest_history_summary_is_human_readable(self) -> None:
        result = {
            "count": 1,
            "items": [
                {
                    "date": "2026-05-15",
                    "chunks_count": 4,
                    "path": "/tmp/memory_wiki/digests/2026-05-15.md",
                    "updated_at": "2026-05-15 10:30:00",
                }
            ],
        }

        summary = build_memory_digest_history_summary(result)

        self.assertIn("Memory digests: 1", summary)
        self.assertIn("2026-05-15", summary)
        self.assertIn("Chunks: 4", summary)


if __name__ == "__main__":
    unittest.main()
