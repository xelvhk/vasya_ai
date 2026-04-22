from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from agents.calendar_agent import handle_calendar_intent
from agents.game_agent import handle_game_intent
from agents.note_agent import handle_note_intent
from agents.task_agent import handle_task_intent
from assistant.child_mode import child_mode_store
from assistant.control import assistant_control
from core.models import IntentResult
from services.github_notion_sync_service import (
    append_note_to_notion,
    read_notion_updates_page,
    sync_project_updates_to_notion,
)
from services.speed_report_service import build_voice_diagnostics_report
from services.os_action_service import execute_os_action
from services.voice_recovery_service import apply_voice_auto_tune_from_metrics, run_voice_mic_test
from services.user_profile_service import (
    forget_user_profile,
    get_user_profile_summary,
    is_clear_all_target,
    remember_user_profile,
    request_clear_user_profile_confirmation,
)
from voice.tts import stop_speaking


ToolHandler = Callable[[IntentResult], str]


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    description: str
    intents: tuple[str, ...]
    handler: ToolHandler


def _run_calendar_tool(intent_result: IntentResult) -> str:
    return handle_calendar_intent(intent_result)


def _run_task_tool(intent_result: IntentResult) -> str:
    return handle_task_intent(intent_result)


def _run_note_tool(intent_result: IntentResult) -> str:
    return handle_note_intent(intent_result)


def _run_game_tool(intent_result: IntentResult) -> str:
    return handle_game_intent(intent_result)


def _run_stop_speaking_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    stop_speaking()
    return ""


def _run_enable_child_mode_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    child_mode_store.enable()
    return (
        "Хорошо. Включил детский режим. "
        "Теперь я буду говорить проще, мягче и без взрослых тем."
    )


def _run_disable_child_mode_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    child_mode_store.disable()
    return "Хорошо. Выключил детский режим."


def _run_exit_assistant_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    stop_speaking()
    assistant_control.request_exit()
    return "Завершаю работу."


def _run_open_text_command_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    assistant_control.request_open_text_command()
    return "Открываю текстовое окно."


def _run_user_profile_tool(intent_result: IntentResult) -> str:
    if intent_result.intent == "remember_user_profile":
        return remember_user_profile(str(intent_result.data.get("memory", "")))
    if intent_result.intent == "forget_user_profile":
        target = str(intent_result.data.get("target", ""))
        if is_clear_all_target(target):
            return request_clear_user_profile_confirmation()
        return forget_user_profile(target)
    return get_user_profile_summary()


def _run_notion_github_sync_tool(intent_result: IntentResult) -> str:
    if intent_result.intent == "sync_github_notion":
        repo = str(intent_result.data.get("repo", "")).strip() or None
        page_id = str(intent_result.data.get("page_id", "")).strip() or None
        hours_raw = intent_result.data.get("hours")
        hours = int(hours_raw) if isinstance(hours_raw, (int, float, str)) and str(hours_raw).strip().isdigit() else None
        return sync_project_updates_to_notion(repo=repo, page_id=page_id, hours=hours)

    if intent_result.intent == "read_notion_page":
        page_id = str(intent_result.data.get("page_id", "")).strip() or None
        return read_notion_updates_page(page_id=page_id, limit=10)

    text = str(intent_result.data.get("text", "")).strip()
    page_id = str(intent_result.data.get("page_id", "")).strip() or None
    return append_note_to_notion(text, page_id=page_id)


def _run_speed_report_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    return build_voice_diagnostics_report(limit=24)


def _run_mic_test_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    return run_voice_mic_test(duration_seconds=2.0)


def _run_auto_tune_voice_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    return apply_voice_auto_tune_from_metrics(limit=40)


def _run_os_action_tool(intent_result: IntentResult) -> str:
    try:
        if intent_result.intent == "os_open_url":
            return execute_os_action("open_url", intent_result.data)
        if intent_result.intent == "os_open_app":
            return execute_os_action("open_app", intent_result.data)
        if intent_result.intent == "os_type_text":
            return execute_os_action("type_text", intent_result.data)
        if intent_result.intent == "os_keypress":
            return execute_os_action("keypress", intent_result.data)
        if intent_result.intent == "os_click":
            return execute_os_action("click", intent_result.data)
        return execute_os_action("scroll", intent_result.data)
    except Exception as exc:
        return f"Не удалось выполнить OS-действие: {exc}"


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        tool_id="calendar",
        description="Работа с календарем и событиями.",
        intents=("create_event", "get_events", "delete_event"),
        handler=_run_calendar_tool,
    ),
    ToolSpec(
        tool_id="tasks",
        description="Работа с задачами.",
        intents=("create_task", "get_tasks", "complete_task", "delete_task", "delete_tasks"),
        handler=_run_task_tool,
    ),
    ToolSpec(
        tool_id="notes",
        description="Локальные заметки и экспорт заметок.",
        intents=("create_note", "get_notes", "export_notes"),
        handler=_run_note_tool,
    ),
    ToolSpec(
        tool_id="games",
        description="Игровой режим и детские игры.",
        intents=("play_game",),
        handler=_run_game_tool,
    ),
    ToolSpec(
        tool_id="stop_speaking",
        description="Остановить текущую озвучку.",
        intents=("stop_speaking",),
        handler=_run_stop_speaking_tool,
    ),
    ToolSpec(
        tool_id="child_mode_enable",
        description="Включить детский режим.",
        intents=("enable_child_mode",),
        handler=_run_enable_child_mode_tool,
    ),
    ToolSpec(
        tool_id="child_mode_disable",
        description="Выключить детский режим.",
        intents=("disable_child_mode",),
        handler=_run_disable_child_mode_tool,
    ),
    ToolSpec(
        tool_id="exit_assistant",
        description="Корректно завершить помощника.",
        intents=("exit_assistant",),
        handler=_run_exit_assistant_tool,
    ),
    ToolSpec(
        tool_id="open_text_command",
        description="Открыть текстовое окно команды.",
        intents=("open_text_command",),
        handler=_run_open_text_command_tool,
    ),
    ToolSpec(
        tool_id="user_profile",
        description="Управление персональной памятью о пользователе.",
        intents=("remember_user_profile", "forget_user_profile", "get_user_profile"),
        handler=_run_user_profile_tool,
    ),
    ToolSpec(
        tool_id="notion_github_sync",
        description="Чтение/запись в Notion и синхронизация последних изменений из GitHub.",
        intents=("sync_github_notion", "read_notion_page", "append_notion_page"),
        handler=_run_notion_github_sync_tool,
    ),
    ToolSpec(
        tool_id="speed_report",
        description="Краткий отчет задержек голосового контура.",
        intents=("speed_report",),
        handler=_run_speed_report_tool,
    ),
    ToolSpec(
        tool_id="mic_test",
        description="Быстрая проверка микрофона.",
        intents=("mic_test",),
        handler=_run_mic_test_tool,
    ),
    ToolSpec(
        tool_id="auto_tune_voice",
        description="Автоматическая подстройка голосовых параметров по последним метрикам.",
        intents=("auto_tune_voice",),
        handler=_run_auto_tune_voice_tool,
    ),
    ToolSpec(
        tool_id="os_actions",
        description="OS-действия: открыть URL/приложение, ввод текста, клавиши, клик и скролл.",
        intents=("os_open_url", "os_open_app", "os_type_text", "os_keypress", "os_click", "os_scroll"),
        handler=_run_os_action_tool,
    ),
)


_TOOLS_BY_INTENT: dict[str, ToolSpec] = {
    intent: spec
    for spec in TOOL_SPECS
    for intent in spec.intents
}


def dispatch_tool(intent_result: IntentResult) -> str | None:
    spec = _TOOLS_BY_INTENT.get(intent_result.intent)
    if spec is None:
        return None
    return spec.handler(intent_result)


def list_tools() -> tuple[ToolSpec, ...]:
    return TOOL_SPECS
