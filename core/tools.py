from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from agents.calendar_agent import handle_calendar_intent
from agents.game_agent import handle_game_intent
from agents.note_agent import handle_note_intent
from agents.task_agent import handle_task_intent
from assistant.child_mode import child_mode_store
from assistant.control import assistant_control
from assistant.dictation_mode import dictation_mode_store
from core.models import IntentResult
from services.github_notion_sync_service import (
    append_note_to_notion,
    read_notion_updates_page,
    sync_project_updates_to_notion,
)
from services.github_obsidian_sync_service import (
    sync_github_project_to_obsidian,
    update_obsidian_note,
)
from services.memory_center_service import (
    build_memory_daily_digest,
    build_memory_center_summary,
    build_memory_digest_summary,
    build_memory_digest_history_summary,
    build_memory_recent_summary,
    build_memory_search_summary,
    get_memory_center_status,
    list_memory_daily_digests,
    list_recent_memory_center,
    search_memory_center,
)
from services.memory_sync_service import sync_memory_source
from services.obsidian_knowledge_service import triage_unstructured_ideas
from services.obsidian_service import resolve_obsidian_vault_path
from services.project_idea_planning_service import handle_project_idea_request
from services.morning_show_service import get_morning_show_message
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


def _run_obsidian_tool(intent_result: IntentResult) -> str:
    if intent_result.intent == "sync_github_obsidian_project":
        repo = str(intent_result.data.get("repo", "")).strip() or None
        return sync_github_project_to_obsidian(repo=repo)
    if intent_result.intent == "analyze_project_idea_to_obsidian":
        idea = str(intent_result.data.get("idea", "")).strip()
        title = str(intent_result.data.get("title", "")).strip() or None
        return handle_project_idea_request(idea=idea, title=title)
    if intent_result.intent == "triage_obsidian_ideas":
        vault_path, error = resolve_obsidian_vault_path()
        if error or vault_path is None:
            return str(error or "Не удалось определить путь к Obsidian vault.")
        result = triage_unstructured_ideas(vault_path)
        if not result.get("ok"):
            return str(result.get("error") or "Не удалось разобрать неразобранные идеи.")
        updated = int(result.get("updated", 0))
        skipped = int(result.get("skipped", 0))
        return (
            "Готово. Разобрала неразобранные идеи в Obsidian: "
            f"обновила {updated}, пропустила {skipped}."
        )
    mode = "replace" if intent_result.intent == "replace_obsidian_note" else "append"
    title = str(intent_result.data.get("title", "")).strip()
    text = str(intent_result.data.get("text", "")).strip()
    return update_obsidian_note(title=title, content=text, mode=mode)


def _run_memory_center_tool(intent_result: IntentResult) -> str:
    if intent_result.intent == "memory_status":
        return build_memory_center_summary(get_memory_center_status())
    if intent_result.intent == "memory_recent":
        return build_memory_recent_summary(list_recent_memory_center(limit=5))
    if intent_result.intent == "memory_digest":
        date_text = str(intent_result.data.get("date", "")).strip() or None
        return build_memory_digest_summary(build_memory_daily_digest(date_text))
    if intent_result.intent == "memory_digest_history":
        return build_memory_digest_history_summary(list_memory_daily_digests(limit=8))
    if intent_result.intent == "memory_sync":
        force = bool(intent_result.data.get("force", False))
        result = sync_memory_source("all", force=force)
        ingested = int(result.get("ingested", 0))
        if result.get("ok"):
            successful = ", ".join(result.get("successful_sources", [])) or "нет новых источников"
            errors = result.get("errors", [])
            warning = f" Есть ошибки по источникам: {len(errors)}." if errors else ""
            return (
                "Memory Center обновлен. "
                f"Источники: {successful}. "
                f"Элементов: {ingested}.{warning}"
            )
        errors = result.get("errors") or []
        if errors:
            details = "; ".join(
                str(item.get("error") or item.get("source") or "unknown")
                for item in errors[:3]
                if isinstance(item, dict)
            )
        else:
            details = str(result.get("error", "unknown error"))
        return f"Не удалось обновить Memory Center: {details}"

    query = str(intent_result.data.get("query", "")).strip()
    if not query:
        return "Что найти в Memory Center?"
    return build_memory_search_summary(search_memory_center(query, limit=5))


def _run_speed_report_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    return build_voice_diagnostics_report(limit=24)


def _run_mic_test_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    return run_voice_mic_test(duration_seconds=2.0)


def _run_auto_tune_voice_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    return apply_voice_auto_tune_from_metrics(limit=40)


def _run_morning_show_tool(intent_result: IntentResult) -> str:
    force = bool(intent_result.data.get("force", False))
    message = get_morning_show_message(force=force, mark_delivered=True)
    if message:
        return message
    return "Доброе утро. Я на связи."


def _run_start_dictation_mode_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    enabled_now = dictation_mode_store.enable()
    if enabled_now:
        return (
            "Включила режим диктовки. "
            "Теперь всё, что ты скажешь, я буду вводить в активное поле. "
            "Для остановки скажи: стоп диктовка."
        )
    return "Режим диктовки уже включен."


def _run_stop_dictation_mode_tool(intent_result: IntentResult) -> str:
    _ = intent_result
    disabled_now = dictation_mode_store.disable()
    if disabled_now:
        return "Остановила режим диктовки."
    return "Режим диктовки уже выключен."


def _run_dictation_mode_tool(intent_result: IntentResult) -> str:
    if intent_result.intent == "start_dictation_mode":
        return _run_start_dictation_mode_tool(intent_result)
    return _run_stop_dictation_mode_tool(intent_result)


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
        tool_id="obsidian_sync",
        description="Обновление заметок Obsidian и создание проектной заметки из GitHub README.",
        intents=(
            "append_obsidian_note",
            "replace_obsidian_note",
            "sync_github_obsidian_project",
            "analyze_project_idea_to_obsidian",
            "triage_obsidian_ideas",
        ),
        handler=_run_obsidian_tool,
    ),
    ToolSpec(
        tool_id="memory_center",
        description="Memory Center: статус, синхронизация и поиск по локальной памяти.",
        intents=(
            "memory_status",
            "memory_sync",
            "memory_search",
            "memory_recent",
            "memory_digest",
            "memory_digest_history",
        ),
        handler=_run_memory_center_tool,
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
        tool_id="morning_show",
        description="Утреннее шоу: погода, задачи и короткая мысль дня.",
        intents=("morning_show",),
        handler=_run_morning_show_tool,
    ),
    ToolSpec(
        tool_id="dictation_mode",
        description="Управление непрерывным режимом диктовки в активное поле.",
        intents=("start_dictation_mode", "stop_dictation_mode"),
        handler=_run_dictation_mode_tool,
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
