from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from services.morning_show_service import MorningBriefResult, build_morning_brief, get_morning_show_message
from services.ollama_client import OllamaClientError
from utils.system_intents import detect_system_intent


class MorningBriefServiceTests(unittest.TestCase):
    def test_builds_brief_with_empty_sources_and_markdown(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch("services.morning_show_service.MEMORY_WIKI_DIR", str(Path(tmp) / "memory_wiki")), patch(
                "services.morning_show_service._get_cached_weather_line",
                return_value=None,
            ), patch(
                "services.morning_show_service._fetch_weather_line",
                return_value=None,
            ), patch("services.morning_show_service.get_tasks", return_value=[]), patch(
                "services.morning_show_service.get_events",
                return_value={"events": [], "google_sync_error": None},
            ), patch(
                "services.morning_show_service.get_memory_center_status",
                return_value={"status": "empty", "sources_count": 0, "chunks_count": 0, "sync_connections": []},
            ), patch(
                "services.morning_show_service.list_recent_memory_center",
                return_value={"items": []},
            ), patch(
                "services.morning_show_service.list_memory_daily_digests",
                return_value={"items": []},
            ):
                result = build_morning_brief(
                    datetime(2026, 5, 28, 9, 0),
                    save_markdown=True,
                    use_llm=False,
                )

            self.assertTrue(result.ok)
            self.assertEqual(result.date, "2026-05-28")
            self.assertEqual(result.sections["tasks"]["open_count"], 0)
            self.assertIn("Погоду", " ".join(result.warnings))
            self.assertIsNotNone(result.markdown_path)
            assert result.markdown_path is not None
            brief_path = Path(result.markdown_path)
            self.assertEqual(brief_path.name, "2026-05-28.md")
            self.assertIn("# Morning Brief 2026-05-28", brief_path.read_text(encoding="utf-8"))

    def test_collector_failure_becomes_warning(self) -> None:
        with patch("services.morning_show_service._fetch_weather_line", return_value="Погода: ясно."), patch(
            "services.morning_show_service.get_tasks",
            side_effect=RuntimeError("db down"),
        ), patch(
            "services.morning_show_service.get_events",
            return_value={"events": [], "google_sync_error": None},
        ), patch(
            "services.morning_show_service.get_memory_center_status",
            return_value={"status": "ready", "sources_count": 1, "chunks_count": 2, "sync_connections": []},
        ), patch(
            "services.morning_show_service.list_recent_memory_center",
            return_value={"items": []},
        ), patch(
            "services.morning_show_service.list_memory_daily_digests",
            return_value={"items": []},
        ):
            result = build_morning_brief(
                datetime(2026, 5, 28, 9, 0),
                save_markdown=False,
                use_llm=False,
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.sections["tasks"]["open_count"], 0)
        self.assertTrue(any("Задачи недоступны" in warning for warning in result.warnings))

    def test_markdown_path_is_stable_for_same_day(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch("services.morning_show_service.MEMORY_WIKI_DIR", str(Path(tmp) / "memory_wiki")), patch(
                "services.morning_show_service._fetch_weather_line",
                return_value="Погода: ясно.",
            ), patch("services.morning_show_service.get_tasks", return_value=[]), patch(
                "services.morning_show_service.get_events",
                return_value={"events": [], "google_sync_error": None},
            ), patch(
                "services.morning_show_service.get_memory_center_status",
                return_value={"status": "empty", "sources_count": 0, "chunks_count": 0, "sync_connections": []},
            ), patch(
                "services.morning_show_service.list_recent_memory_center",
                return_value={"items": []},
            ), patch(
                "services.morning_show_service.list_memory_daily_digests",
                return_value={"items": []},
            ):
                first = build_morning_brief(datetime(2026, 5, 28, 8, 0), use_llm=False)
                second = build_morning_brief(datetime(2026, 5, 28, 9, 0), use_llm=False)

            self.assertEqual(first.markdown_path, second.markdown_path)

    def test_markdown_write_failure_returns_warning(self) -> None:
        with patch("services.morning_show_service._fetch_weather_line", return_value="Погода: ясно."), patch(
            "services.morning_show_service.get_tasks",
            return_value=[],
        ), patch(
            "services.morning_show_service.get_events",
            return_value={"events": [], "google_sync_error": None},
        ), patch(
            "services.morning_show_service.get_memory_center_status",
            return_value={"status": "empty", "sources_count": 0, "chunks_count": 0, "sync_connections": []},
        ), patch(
            "services.morning_show_service.list_recent_memory_center",
            return_value={"items": []},
        ), patch(
            "services.morning_show_service.list_memory_daily_digests",
            return_value={"items": []},
        ), patch(
            "services.morning_show_service._write_morning_brief_markdown",
            side_effect=OSError("read-only"),
        ):
            result = build_morning_brief(
                datetime(2026, 5, 28, 9, 0),
                save_markdown=True,
                use_llm=False,
            )

        self.assertTrue(result.ok)
        self.assertIsNone(result.markdown_path)
        self.assertTrue(any("Markdown-брифинг" in warning for warning in result.warnings))

    def test_markdown_escapes_untrusted_list_text(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch("services.morning_show_service.MEMORY_WIKI_DIR", str(Path(tmp) / "memory_wiki")), patch(
                "services.morning_show_service._fetch_weather_line",
                return_value="Погода: ясно.",
            ), patch(
                "services.morning_show_service.get_tasks",
                return_value=[{"id": 1, "task": "Safe\n- [ ] injected", "datetime": "2026-05-28 10:00"}],
            ), patch(
                "services.morning_show_service.get_events",
                return_value={"events": [{"id": 2, "title": "Demo [link](bad)", "datetime": "2026-05-28 11:00"}]},
            ), patch(
                "services.morning_show_service.get_memory_center_status",
                return_value={"status": "ready", "sources_count": 1, "chunks_count": 1, "sync_connections": []},
            ), patch(
                "services.morning_show_service.list_recent_memory_center",
                return_value={"items": [{"title": "Memory *bold*", "source_key": "github", "snippet": "line\n# heading"}]},
            ), patch(
                "services.morning_show_service.list_memory_daily_digests",
                return_value={"items": []},
            ):
                result = build_morning_brief(
                    datetime(2026, 5, 28, 9, 0),
                    save_markdown=True,
                    use_llm=False,
                )

            assert result.markdown_path is not None
            markdown = Path(result.markdown_path).read_text(encoding="utf-8")

        self.assertIn("Safe - \\[ \\] injected", markdown)
        self.assertIn("Demo \\[link\\]\\(bad\\)", markdown)
        self.assertIn("Memory \\*bold\\*", markdown)
        self.assertIn("line \\# heading", markdown)

    def test_ollama_failure_uses_template_fallback(self) -> None:
        with patch("services.morning_show_service._fetch_weather_line", return_value="Погода: ясно."), patch(
            "services.morning_show_service.get_tasks",
            return_value=[],
        ), patch(
            "services.morning_show_service.get_events",
            return_value={"events": [], "google_sync_error": None},
        ), patch(
            "services.morning_show_service.get_memory_center_status",
            return_value={"status": "empty", "sources_count": 0, "chunks_count": 0, "sync_connections": []},
        ), patch(
            "services.morning_show_service.list_recent_memory_center",
            return_value={"items": []},
        ), patch(
            "services.morning_show_service.list_memory_daily_digests",
            return_value={"items": []},
        ), patch(
            "services.morning_show_service.generate",
            side_effect=OllamaClientError("offline"),
        ):
            result = build_morning_brief(
                datetime(2026, 5, 28, 9, 0),
                save_markdown=False,
                use_llm=True,
            )

        self.assertIn("Доброе утро. Брифинг", result.spoken_summary)

    def test_morning_show_message_returns_summary_with_markdown_path(self) -> None:
        brief = MorningBriefResult(
            ok=True,
            date="2026-05-28",
            spoken_summary="Доброе утро. Брифинг готов.",
            markdown_path="/tmp/brief.md",
            sections={},
            warnings=[],
        )
        with patch("services.morning_show_service.build_morning_brief", return_value=brief):
            response = get_morning_show_message(
                datetime(2026, 5, 28, 9, 0),
                force=True,
                mark_delivered=False,
            )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("Полный брифинг", response)

    def test_morning_brief_phrase_routes_to_morning_show(self) -> None:
        intent = detect_system_intent("утренний брифинг")

        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "morning_show")
        self.assertEqual(intent.data, {"force": True})


if __name__ == "__main__":
    unittest.main()
