from __future__ import annotations

from assistant.state import AssistantState, AssistantStateName


def state_label(state_name: AssistantStateName) -> str:
    if state_name == AssistantStateName.LISTENING:
        return "слушает"
    if state_name == AssistantStateName.THINKING:
        return "думает"
    if state_name == AssistantStateName.SPEAKING:
        return "говорит"
    if state_name == AssistantStateName.ERROR:
        return "ошибка"
    return "в покое"


def bubble_text(state: AssistantState) -> str:
    if state.message:
        return state.message.strip()
    if state.name == AssistantStateName.LISTENING:
        return "Слушаю..."
    if state.name == AssistantStateName.THINKING:
        return "Думаю..."
    if state.name == AssistantStateName.SPEAKING:
        return "Отвечаю..."
    if state.name == AssistantStateName.ERROR:
        return "Что-то пошло не так"
    return ""


def visible_response_bubble_text(
    state: AssistantState,
    *,
    show_response_bubble: bool,
    widget_visible: bool,
) -> str | None:
    text = bubble_text(state)
    if (
        not show_response_bubble
        or not text
        or state.name == AssistantStateName.IDLE
        or not widget_visible
    ):
        return None
    if len(text) > 110:
        return f"{text[:107]}..."
    return text


def hover_hint_text(
    state: AssistantState,
    *,
    thinking_seconds: int,
    voice_health_hint: str,
) -> str:
    if state.name == AssistantStateName.LISTENING:
        return "Слушаю…"
    if state.name == AssistantStateName.THINKING:
        return f"Думаю… {max(1, thinking_seconds)}с"
    if state.name == AssistantStateName.SPEAKING:
        return "Говорю…"
    if state.name == AssistantStateName.ERROR:
        message = (state.message or "").lower()
        if "тихо" in message:
            return "Слишком тихо — скажи громче"
        if "не расслыш" in message:
            return "Не расслышал — повтори"
        if "сомнева" in message:
            return "Сомневаюсь — повтори"
        return "Не понял — повтори"
    return f"Клик — говорить • ПКМ — меню\n{voice_health_hint}"


def tray_tooltip_text(
    state: AssistantState,
    *,
    thinking_seconds: int,
    voice_health_hint: str,
) -> str:
    suffix = ""
    if state.name != AssistantStateName.IDLE:
        suffix = f" [{state_label(state.name)}]"
        if state.name == AssistantStateName.THINKING:
            suffix = f"{suffix} {max(1, thinking_seconds)}с"
        elif state.message:
            detail = " ".join(state.message.split())
            if len(detail) > 56:
                detail = f"{detail[:53]}..."
            suffix = f"{suffix} • {detail}"
    else:
        suffix = f" • {voice_health_hint}"
    return f"Вася AI{suffix}"
