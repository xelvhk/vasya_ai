from __future__ import annotations

import types
import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient

    from apps.api import main as api_main

    _FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    _FASTAPI_AVAILABLE = False


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi is not installed in the current virtual environment")
class ApiMorningBriefRoutesTests(unittest.TestCase):
    def test_morning_brief_route_returns_expected_payload(self) -> None:
        brief = types.SimpleNamespace(
            to_dict=lambda: {
                "ok": True,
                "date": "2026-05-28",
                "spoken_summary": "Доброе утро. Брифинг готов.",
                "markdown_path": "/tmp/memory_wiki/briefings/2026-05-28.md",
                "sections": {"tasks": {"open_count": 0}},
                "warnings": [],
            }
        )
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.routes.morning_brief.build_morning_brief",
            return_value=brief,
        ) as build_mock:
            with TestClient(api_main.app) as client:
                response = client.post(
                    "/v1/morning-brief",
                    json={"save_markdown": True, "use_llm": False},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["date"], "2026-05-28")
        self.assertIn("Брифинг", payload["spoken_summary"])
        self.assertEqual(payload["sections"]["tasks"]["open_count"], 0)
        build_mock.assert_called_once_with(save_markdown=True, use_llm=False)


if __name__ == "__main__":
    unittest.main()
