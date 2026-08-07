from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apps.api.routes.chat import chat
from apps.api.routes.realtime import pipeline as run_api_pipeline
from apps.api.schemas import ChatRequest, PipelineRequest
from config.projects import ProjectConfig
from core.orchestrator import ProcessResult, process_text_detailed
from services.project_registry_service import (
    ProjectStatus,
    build_project_status_summary,
    project_dashboard_target,
    resolve_project_reference,
)
from utils.intent_fastpaths import detect_fast_intent
from voice.pipeline import PipelineEvent, run_text_pipeline


class ProjectOsCommandTests(unittest.TestCase):
    def test_detects_project_status_summary_commands_without_llm(self) -> None:
        for text in ("что дальше по проектам?", "what is next by projects?"):
            with self.subTest(text=text):
                intent = detect_fast_intent(text)

                self.assertIsNotNone(intent)
                assert intent is not None
                self.assertEqual(intent.intent, "project_status_summary")
                self.assertEqual(intent.data, {})

    def test_detects_open_project_command_without_treating_it_as_an_app(self) -> None:
        intent = detect_fast_intent("открой ai_pal")

        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "open_project_dashboard")
        self.assertEqual(intent.data, {"project": "ai_pal"})

    def test_open_project_command_does_not_override_existing_app_command(self) -> None:
        intent = detect_fast_intent("открой браузер")

        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "os_open_app")

    def test_open_project_command_does_not_override_existing_task_command(self) -> None:
        intent = detect_fast_intent("покажи задачи")

        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "get_tasks")

    def test_summary_is_concise_and_reports_clean_dirty_and_warning_states(self) -> None:
        statuses = [
            ProjectStatus(
                id="ai_pal",
                name="Vasya AI",
                path="/projects/ai_pal",
                kind="python",
                priority=10,
                exists=True,
                status="OK",
                warning=None,
                branch="main",
                dirty=True,
                latest_commit="abc123 Add status",
                next_action="Review project status.",
            ),
            ProjectStatus(
                id="portfolio",
                name="Portfolio",
                path="/projects/portfolio",
                kind="web",
                priority=20,
                exists=False,
                status="WARN",
                warning="project path is missing",
                branch=None,
                dirty=None,
                latest_commit=None,
                next_action="Add or fix the project path.",
            ),
        ]

        summary = build_project_status_summary(statuses)

        self.assertEqual(
            summary,
            "По проектам: Vasya AI — main, есть незакоммиченные изменения; "
            "Portfolio — требует внимания. Ближайший шаг: Review project status.",
        )

    def test_summary_explains_empty_registry(self) -> None:
        self.assertEqual(
            build_project_status_summary([]),
            "В Vasya Project OS пока нет добавленных проектов.",
        )

    def test_project_reference_matches_id_and_display_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = (
                ProjectConfig("ai_pal", "Vasya AI", Path(tmp), "python", 10),
                ProjectConfig("portfolio", "Portfolio", Path(tmp), "web", 20),
            )

            by_id = resolve_project_reference("ai pal", projects)
            by_name = resolve_project_reference("Vasya AI", projects)

        self.assertEqual(by_id.id if by_id else None, "ai_pal")
        self.assertEqual(by_name.id if by_name else None, "ai_pal")
        self.assertIsNone(resolve_project_reference("unknown", projects))

    def test_dashboard_target_is_local_and_stable(self) -> None:
        self.assertEqual(project_dashboard_target("ai_pal"), "/control-center#project-ai_pal")

    def test_open_project_returns_navigation_target_without_os_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = (ProjectConfig("ai_pal", "Vasya AI", Path(tmp), "python", 10),)
            with patch(
                "services.project_registry_service.configured_project_configs",
                return_value=projects,
            ), patch("core.orchestrator.log_interaction_event"), patch(
                "core.tools.execute_os_action"
            ) as os_action:
                result = process_text_detailed("открой ai_pal")

        self.assertEqual(result.intent, "open_project_dashboard")
        self.assertEqual(result.response, "Открываю Vasya AI в Vasya Project OS.")
        self.assertEqual(result.navigation_target, "/control-center#project-ai_pal")
        os_action.assert_not_called()

    def test_unknown_project_does_not_create_navigation_target(self) -> None:
        with patch(
            "services.project_registry_service.configured_project_configs",
            return_value=(),
        ), patch("core.orchestrator.log_interaction_event"):
            result = process_text_detailed("открой ai_pal")

        self.assertEqual(result.intent, "open_project_dashboard")
        self.assertEqual(result.response, "Не нашла проект «ai_pal» в Vasya Project OS.")
        self.assertIsNone(result.navigation_target)

    def test_chat_api_exposes_navigation_target(self) -> None:
        result = ProcessResult(
            intent="open_project_dashboard",
            response="Открываю Vasya AI в Vasya Project OS.",
            navigation_target="/control-center#project-ai_pal",
        )
        with patch("apps.api.routes.chat.process_text_detailed", return_value=result), patch(
            "apps.api.routes.chat.log_interaction_event"
        ):
            response = chat(ChatRequest(text="открой ai_pal"))

        self.assertEqual(response.navigation_target, "/control-center#project-ai_pal")

    def test_pipeline_api_exposes_navigation_target(self) -> None:
        events = [
            PipelineEvent(
                type="intent",
                stage="intent_resolved",
                ts_ms=1.0,
                data={
                    "intent": "open_project_dashboard",
                    "needs_followup": False,
                    "navigation_target": "/control-center#project-ai_pal",
                },
            ),
            PipelineEvent(
                type="response_chunk",
                stage="response_stream",
                ts_ms=2.0,
                data={"text": "Открываю Vasya AI."},
            ),
            PipelineEvent(
                type="done",
                stage="pipeline_done",
                ts_ms=3.0,
                data={"metrics": {"total_ms": 3.0}},
            ),
        ]
        with patch("apps.api.routes.realtime.run_text_pipeline", return_value=iter(events)), patch(
            "apps.api.routes.realtime.log_interaction_event"
        ):
            response = run_api_pipeline(PipelineRequest(text="открой ai_pal"))

        self.assertEqual(response.navigation_target, "/control-center#project-ai_pal")

    def test_voice_pipeline_exposes_navigation_target_on_intent_event(self) -> None:
        result = ProcessResult(
            intent="open_project_dashboard",
            response="Открываю Vasya AI в Vasya Project OS.",
            navigation_target="/control-center#project-ai_pal",
        )
        with patch("voice.pipeline.process_text_detailed", return_value=result), patch(
            "voice.pipeline.log_interaction_event"
        ):
            events = list(run_text_pipeline("открой ai_pal"))

        intent_event = next(event for event in events if event.stage == "intent_resolved")
        self.assertEqual(
            intent_event.data.get("navigation_target"),
            "/control-center#project-ai_pal",
        )


if __name__ == "__main__":
    unittest.main()
