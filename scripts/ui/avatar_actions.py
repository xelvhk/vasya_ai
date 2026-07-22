from __future__ import annotations

from dataclasses import dataclass

from assistant.state import AssistantStateName


@dataclass(frozen=True)
class VoiceActivationDecision:
    action: str
    log_event: str
    state_name: AssistantStateName | None = None
    state_message: str = ""
    stop_speaking: bool = False
    queue_activation: bool = False


@dataclass(frozen=True)
class TextCommandDecision:
    action: str
    state_name: AssistantStateName | None = None
    state_message: str = ""
    stop_speaking: bool = False
    queue_command: bool = False
    cancel_current: bool = False


def voice_activation_decision(
    *,
    interaction_locked: bool,
    current_state_name: AssistantStateName,
) -> VoiceActivationDecision:
    if not interaction_locked:
        return VoiceActivationDecision(
            action="start",
            log_event="widget_activation_started",
        )
    if current_state_name == AssistantStateName.SPEAKING:
        return VoiceActivationDecision(
            action="interrupt_speaking",
            log_event="widget_activation_interrupt_speaking",
            state_name=AssistantStateName.IDLE,
            state_message="Остановила озвучивание. Нажми еще раз, чтобы говорить.",
            stop_speaking=True,
        )
    return VoiceActivationDecision(
        action="queue",
        log_event="widget_activation_queued reason=interaction_in_progress",
        state_name=AssistantStateName.THINKING,
        state_message="Заканчиваю текущий запрос и сразу начну слушать.",
        queue_activation=True,
    )


def text_command_decision(
    *,
    interaction_locked: bool,
    has_cancel_event: bool,
) -> TextCommandDecision:
    if not interaction_locked:
        return TextCommandDecision(action="start")
    if has_cancel_event:
        return TextCommandDecision(
            action="replace_current",
            state_name=AssistantStateName.THINKING,
            state_message="Останавливаю текущий ответ и переключаюсь на новую команду...",
            stop_speaking=True,
            queue_command=True,
            cancel_current=True,
        )
    return TextCommandDecision(
        action="wait",
        state_name=AssistantStateName.THINKING,
        state_message="Секунду, сначала закончу текущий запрос.",
    )
