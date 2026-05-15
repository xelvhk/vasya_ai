from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient

    from apps.api import main as api_main

    _FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    _FASTAPI_AVAILABLE = False


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi is not installed in the current virtual environment")
class ApiMemoryRoutesTests(unittest.TestCase):
    def test_memory_status_returns_center_metrics(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch("storage.db.STORAGE_DB_FILE", str(Path(tmp) / "vasya.db")), patch(
                "services.memory_center_service.MEMORY_WIKI_DIR",
                str(Path(tmp) / "memory_wiki"),
            ), patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False):
                with TestClient(api_main.app) as client:
                    response = client.get("/v1/memory/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["sources_count"], 0)
        self.assertEqual(payload["chunks_count"], 0)
        self.assertEqual(payload["status"], "empty")

    def test_memory_search_returns_results(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch("storage.db.STORAGE_DB_FILE", str(Path(tmp) / "vasya.db")), patch(
                "services.memory_center_service.MEMORY_WIKI_DIR",
                str(Path(tmp) / "memory_wiki"),
            ), patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False):
                from services.memory_center_service import MemoryCenterService

                service = MemoryCenterService(wiki_dir=Path(tmp) / "memory_wiki")
                service.ingest_text(
                    source_key="github",
                    source_name="GitHub",
                    title="Memory Search",
                    content="Search should return provenance links.",
                    external_id="search-1",
                )
                with TestClient(api_main.app) as client:
                    response = client.get("/v1/memory/search", params={"query": "provenance"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["title"], "Memory Search")

    def test_memory_recent_returns_latest_items(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch("storage.db.STORAGE_DB_FILE", str(Path(tmp) / "vasya.db")), patch(
                "services.memory_center_service.MEMORY_WIKI_DIR",
                str(Path(tmp) / "memory_wiki"),
            ), patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False):
                from services.memory_center_service import MemoryCenterService

                service = MemoryCenterService(wiki_dir=Path(tmp) / "memory_wiki")
                service.ingest_text(
                    source_key="github",
                    source_name="GitHub",
                    title="Recent Memory",
                    content="Recent content.",
                    external_id="recent-1",
                )
                with TestClient(api_main.app) as client:
                    response = client.get("/v1/memory/recent", params={"limit": 5})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["title"], "Recent Memory")


if __name__ == "__main__":
    unittest.main()
