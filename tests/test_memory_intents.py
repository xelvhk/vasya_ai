from __future__ import annotations

from datetime import date
import unittest
from unittest.mock import patch

from core.models import IntentResult
from utils.intent_fastpaths import detect_fast_intent


class MemoryIntentFastpathTests(unittest.TestCase):
    def test_memory_status_phrase_routes_to_memory_status(self) -> None:
        intent = detect_fast_intent("покажи статус памяти")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "memory_status")
        self.assertEqual(intent.data, {})

    def test_memory_sync_phrase_routes_to_memory_sync(self) -> None:
        intent = detect_fast_intent("синхронизируй память")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "memory_sync")
        self.assertEqual(intent.data, {"force": True})

    def test_memory_search_phrase_routes_with_query(self) -> None:
        intent = detect_fast_intent("найди в памяти архитектурное решение")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "memory_search")
        self.assertEqual(intent.data, {"query": "архитектурное решение"})

    def test_memory_recent_phrase_routes_to_memory_recent(self) -> None:
        intent = detect_fast_intent("что нового в памяти")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "memory_recent")
        self.assertEqual(intent.data, {})

    def test_memory_digest_phrase_routes_to_memory_digest(self) -> None:
        intent = detect_fast_intent("собери дайджест памяти")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "memory_digest")
        self.assertEqual(intent.data, {})

    def test_memory_digest_history_phrase_routes_to_memory_digest_history(self) -> None:
        intent = detect_fast_intent("покажи дайджесты памяти")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "memory_digest_history")
        self.assertEqual(intent.data, {})

    def test_memory_digest_history_week_phrase_routes_with_range(self) -> None:
        intent = detect_fast_intent("дайджесты памяти за неделю")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "memory_digest_history")
        self.assertEqual(intent.data, {"range": "7d"})

    def test_memory_digest_history_month_phrase_routes_with_range(self) -> None:
        intent = detect_fast_intent("дайджесты памяти за месяц")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "memory_digest_history")
        self.assertEqual(intent.data, {"range": "30d"})


class MemoryToolDispatchTests(unittest.TestCase):
    def test_memory_search_tool_returns_search_summary(self) -> None:
        from core.tools import dispatch_tool

        with patch(
            "core.tools.search_memory_center",
            return_value={
                "query": "memory",
                "count": 1,
                "items": [
                    {
                        "title": "Memory Search",
                        "source_key": "github",
                        "snippet": "Search should return memory provenance links.",
                        "markdown_path": "/tmp/memory.md",
                    }
                ],
            },
        ):
            response = dispatch_tool(IntentResult(intent="memory_search", data={"query": "memory"}))

        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("Memory Search", response)
        self.assertIn("/tmp/memory.md", response)

    def test_memory_digest_tool_returns_digest_summary(self) -> None:
        from core.tools import dispatch_tool

        with patch(
            "core.tools.build_memory_daily_digest",
            return_value={
                "ok": True,
                "date": "2026-05-15",
                "count": 2,
                "path": "/tmp/memory_wiki/digests/2026-05-15.md",
            },
        ):
            response = dispatch_tool(IntentResult(intent="memory_digest", data={}))

        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("Memory digest 2026-05-15", response)
        self.assertIn("/tmp/memory_wiki/digests/2026-05-15.md", response)

    def test_memory_digest_history_tool_returns_history_summary(self) -> None:
        from core.tools import dispatch_tool

        with patch(
            "core.tools.list_memory_daily_digests",
            return_value={
                "count": 1,
                "items": [
                    {
                        "date": "2026-05-15",
                        "chunks_count": 3,
                        "path": "/tmp/memory_wiki/digests/2026-05-15.md",
                    }
                ],
            },
        ):
            response = dispatch_tool(IntentResult(intent="memory_digest_history", data={}))

        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("Memory digests: 1", response)
        self.assertIn("2026-05-15", response)

    def test_memory_digest_history_tool_applies_week_range(self) -> None:
        from core.tools import dispatch_tool

        with patch("core.tools.date") as mock_date, patch(
            "core.tools.list_memory_daily_digests",
            return_value={"count": 0, "items": []},
        ) as list_mock:
            mock_date.today.return_value = date(2026, 5, 17)
            response = dispatch_tool(IntentResult(intent="memory_digest_history", data={"range": "7d"}))

        self.assertIsNotNone(response)
        list_mock.assert_called_once_with(limit=8, date_from="2026-05-11", date_to="2026-05-17")


if __name__ == "__main__":
    unittest.main()
