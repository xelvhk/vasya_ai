from __future__ import annotations

import importlib
import sys
import types
import unittest
from dataclasses import dataclass
from unittest.mock import Mock


class _Dumpable:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self) -> dict:
        return dict(self._payload)


def _clear_modules(*names: str) -> None:
    for name in names:
        sys.modules.pop(name, None)


class TaskServiceSmokeTests(unittest.TestCase):
    def test_create_task_and_list_tasks(self) -> None:
        repo_instance = Mock()
        repo_instance.create.return_value = _Dumpable(
            {"id": 1, "task": "Buy milk", "completed": False}
        )
        repo_instance.list_all.return_value = [
            _Dumpable({"id": 1, "task": "Buy milk", "completed": False}),
            _Dumpable({"id": 2, "task": "Read docs", "completed": True}),
        ]

        repo_module = types.ModuleType("repositories.task_repository")

        class TaskRepository:
            def __new__(cls):  # noqa: D401
                return repo_instance

        repo_module.TaskRepository = TaskRepository

        _clear_modules("services.task_service", "repositories.task_repository")
        sys.modules["repositories.task_repository"] = repo_module
        task_service = importlib.import_module("services.task_service")

        created = task_service.create_task("Buy milk")
        listed = task_service.get_tasks()

        repo_instance.create.assert_called_once_with("Buy milk", dt=None)
        self.assertEqual(created["task"], "Buy milk")
        self.assertEqual(len(listed), 2)
        self.assertTrue(listed[1]["completed"])


class CalendarServiceSmokeTests(unittest.TestCase):
    def test_create_event_local_and_filter_events(self) -> None:
        repo_instance = Mock()
        repo_instance.create.return_value = _Dumpable(
            {
                "id": 11,
                "title": "Planning",
                "datetime": "2026-04-25 10:00",
                "source": "local",
                "external_id": None,
            }
        )
        repo_instance.list_all.return_value = [
            _Dumpable({"id": 11, "title": "Planning", "datetime": "2026-04-25 10:00"}),
            _Dumpable({"id": 12, "title": "Demo", "datetime": "2026-04-26 10:00"}),
        ]

        config_module = types.ModuleType("config.settings")
        config_module.GOOGLE_CALENDAR_ENABLED = False
        config_module.GOOGLE_CALENDAR_SYNC_ON_READ = False

        repo_module = types.ModuleType("repositories.event_repository")

        class EventRepository:
            def __new__(cls):  # noqa: D401
                return repo_instance

        repo_module.EventRepository = EventRepository

        google_module = types.ModuleType("services.google_calendar_client")

        class GoogleCalendarError(Exception):
            pass

        google_module.GoogleCalendarError = GoogleCalendarError
        google_module.create_google_calendar_event = Mock(return_value="ext-1")
        google_module.list_google_calendar_events = Mock(return_value=[])

        _clear_modules(
            "services.calendar_service",
            "config.settings",
            "repositories.event_repository",
            "services.google_calendar_client",
        )
        sys.modules["config.settings"] = config_module
        sys.modules["repositories.event_repository"] = repo_module
        sys.modules["services.google_calendar_client"] = google_module

        calendar_service = importlib.import_module("services.calendar_service")
        created = calendar_service.create_event("Planning", "2026-04-25 10:00")
        filtered = calendar_service.get_events(filter_date="2026-04-25")

        self.assertEqual(created["source"], "local")
        self.assertEqual(len(filtered["events"]), 1)
        self.assertEqual(filtered["events"][0]["title"], "Planning")
        self.assertIsNone(filtered["google_sync_error"])


class ChatRouteSmokeTests(unittest.TestCase):
    def test_chat_route_returns_expected_payload(self) -> None:
        fastapi_module = types.ModuleType("fastapi")

        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class APIRouter:
            def __init__(self, *args, **kwargs):
                pass

            def post(self, *args, **kwargs):
                def decorator(fn):
                    return fn

                return decorator

        fastapi_module.HTTPException = HTTPException
        fastapi_module.APIRouter = APIRouter

        schemas_module = types.ModuleType("apps.api.schemas")

        @dataclass
        class ChatRequest:
            text: str

        @dataclass
        class ChatResponse:
            intent: str
            response: str
            needs_followup: bool

        schemas_module.ChatRequest = ChatRequest
        schemas_module.ChatResponse = ChatResponse

        orchestrator_module = types.ModuleType("core.orchestrator")
        orchestrator_module.process_text_detailed = Mock(
            return_value=types.SimpleNamespace(
                intent="chat",
                response="Привет! Чем помочь?",
                needs_followup=True,
            )
        )

        _clear_modules("apps.api.routes.chat", "fastapi", "apps.api.schemas", "core.orchestrator")
        sys.modules["fastapi"] = fastapi_module
        sys.modules["apps.api.schemas"] = schemas_module
        sys.modules["core.orchestrator"] = orchestrator_module

        chat_route = importlib.import_module("apps.api.routes.chat")

        response = chat_route.chat(ChatRequest(text="привет"))
        self.assertEqual(response.intent, "chat")
        self.assertIn("Чем помочь", response.response)
        self.assertTrue(response.needs_followup)


if __name__ == "__main__":
    unittest.main()
