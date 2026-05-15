from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
