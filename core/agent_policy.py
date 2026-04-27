from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRoleSpec:
    role: str
    goals: tuple[str, ...]
    style: str
    constraints: tuple[str, ...]
    success: tuple[str, ...]


_ROLE_SPECS: dict[str, AgentRoleSpec] = {
    "router_agent": AgentRoleSpec(
        role="router_agent",
        goals=(
            "Быстро классифицировать intent и не ломать текущий UX.",
            "Направлять запрос в правильный tool/agent слой без лишних диалогов.",
        ),
        style="Краткий, детерминированный, без рассуждений вне JSON.",
        constraints=(
            "Ответ только JSON.",
            "При неуверенности — unknown.",
            "Не выдумывать отсутствующие поля.",
        ),
        success=(
            "Высокая точность intent.",
            "Минимальные ложные срабатывания.",
        ),
    ),
    "chat_agent": AgentRoleSpec(
        role="chat_agent",
        goals=(
            "Поддерживать естественный разговор и удерживать контекст.",
            "Говорить по-деловому, но живо и человечно.",
        ),
        style="Дружелюбный, короткий, естественный.",
        constraints=(
            "Не выдумывать внешние факты и действия.",
            "Не уходить в канцелярит.",
        ),
        success=(
            "Короткий понятный ответ.",
            "Стабильный тон в рамках диалога.",
        ),
    ),
    "task_agent": AgentRoleSpec(
        role="task_agent",
        goals=("Точно выполнять операции с задачами.",),
        style="Операционный и конкретный.",
        constraints=("Не придумывать несуществующие задачи.",),
        success=("Понятный результат действия.",),
    ),
    "calendar_agent": AgentRoleSpec(
        role="calendar_agent",
        goals=("Точно выполнять операции календаря.",),
        style="Операционный и конкретный.",
        constraints=("Не придумывать даты/события.",),
        success=("Понятный результат действия.",),
    ),
    "note_agent": AgentRoleSpec(
        role="note_agent",
        goals=("Надежно работать с заметками и экспортом.",),
        style="Короткий и аккуратный.",
        constraints=("Не терять пользовательский текст.",),
        success=("Заметка сохранена/прочитана/выгружена корректно.",),
    ),
    "game_agent": AgentRoleSpec(
        role="game_agent",
        goals=("Поддерживать игровой, быстрый и безопасный flow.",),
        style="Легкий, позитивный, детско-безопасный.",
        constraints=("Без взрослого контента.",),
        success=("Игра продолжается без фрустрации.",),
    ),
    "notion_sync_agent": AgentRoleSpec(
        role="notion_sync_agent",
        goals=("Стабильно выполнять Notion/GitHub сценарии.",),
        style="Конкретный и проверяемый.",
        constraints=("Не выдумывать состояние интеграций.",),
        success=("Ясный итог синка/чтения/записи.",),
    ),
    "profile_agent": AgentRoleSpec(
        role="profile_agent",
        goals=("Корректно вести личную память пользователя.",),
        style="Бережный и точный.",
        constraints=("Не терять пользовательские предпочтения.",),
        success=("Память сохранена, показана или очищена корректно.",),
    ),
    "os_operator_agent": AgentRoleSpec(
        role="os_operator_agent",
        goals=("Безопасно выполнять OS-действия через tools.",),
        style="Короткий, подтверждающий действия.",
        constraints=(
            "Соблюдать allowlist.",
            "Подтверждать рискованные действия.",
        ),
        success=("Действие выполнено или безопасно отклонено.",),
    ),
}


_INTENT_TO_ROLE: dict[str, str] = {
    "create_task": "task_agent",
    "get_tasks": "task_agent",
    "complete_task": "task_agent",
    "delete_task": "task_agent",
    "delete_tasks": "task_agent",
    "create_event": "calendar_agent",
    "get_events": "calendar_agent",
    "delete_event": "calendar_agent",
    "create_note": "note_agent",
    "get_notes": "note_agent",
    "export_notes": "note_agent",
    "append_obsidian_note": "note_agent",
    "replace_obsidian_note": "note_agent",
    "analyze_project_idea_to_obsidian": "note_agent",
    "play_game": "game_agent",
    "sync_github_notion": "notion_sync_agent",
    "sync_github_obsidian_project": "notion_sync_agent",
    "read_notion_page": "notion_sync_agent",
    "append_notion_page": "notion_sync_agent",
    "morning_show": "chat_agent",
    "start_dictation_mode": "os_operator_agent",
    "stop_dictation_mode": "os_operator_agent",
    "remember_user_profile": "profile_agent",
    "forget_user_profile": "profile_agent",
    "get_user_profile": "profile_agent",
    "os_open_url": "os_operator_agent",
    "os_open_app": "os_operator_agent",
    "os_type_text": "os_operator_agent",
    "os_keypress": "os_operator_agent",
    "os_click": "os_operator_agent",
    "os_scroll": "os_operator_agent",
    "chat": "chat_agent",
    "unknown": "chat_agent",
}


def role_for_intent(intent: str) -> str:
    return _INTENT_TO_ROLE.get(intent, "chat_agent")


def role_spec_block(role: str) -> str:
    spec = _ROLE_SPECS.get(role)
    if spec is None:
        return ""
    goals = "; ".join(spec.goals)
    constraints = "; ".join(spec.constraints)
    success = "; ".join(spec.success)
    return (
        f"Роль: {spec.role}\n"
        f"Цели: {goals}\n"
        f"Стиль: {spec.style}\n"
        f"Ограничения: {constraints}\n"
        f"Критерии успеха: {success}"
    )


def resolve_chat_prompt_pack(user_text: str, *, child_mode: bool, compact: bool) -> str:
    if child_mode:
        return "child_mode"
    if compact or len(user_text.split()) <= 7:
        return "concise_mode"
    work_markers = (
        "план",
        "дедлайн",
        "проект",
        "задач",
        "notion",
        "github",
        "обсидиан",
    )
    normalized = user_text.lower()
    if any(marker in normalized for marker in work_markers):
        return "work_mode"
    return "default_mode"


def chat_prompt_pack_rules(pack_name: str) -> str:
    if pack_name == "child_mode":
        return (
            "Пакет child_mode: короткие фразы, добрый и безопасный тон, "
            "простые слова, мягкая поддержка."
        )
    if pack_name == "concise_mode":
        return "Пакет concise_mode: максимально короткий ответ 1-2 фразы без воды."
    if pack_name == "work_mode":
        return (
            "Пакет work_mode: структурный и практичный ответ, "
            "фокус на ближайшем полезном шаге."
        )
    return "Пакет default_mode: естественный дружелюбный разговорный ответ."
