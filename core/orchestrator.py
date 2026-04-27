from assistant.confirmations import classify_confirmation_reply, confirmation_store
from assistant.games import game_store
from agents.task_agent import confirm_delete_all_tasks
from core.handoffs import build_handoffs
from core.agent_policy import role_for_intent
from core.models import IntentResult
from services.game_service import handle_active_game_turn
from services.os_action_service import confirm_os_action
from services.project_idea_planning_service import (
    continue_project_idea_clarification,
    has_pending_project_idea_clarification,
)
from services.user_profile_service import confirm_clear_user_profile
from core.intent_parser import parse_intent
from core.router import route_intent
from services.ollama_client import OllamaClientError
from utils.logger import log_interaction_event
from utils.system_intents import detect_system_intent
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ProcessResult:
    intent: str
    response: str
    role: str = "chat_agent"
    needs_followup: bool = False


@dataclass(frozen=True)
class RoutingStep:
    name: str
    handler: Callable[[str], ProcessResult | None]


def process_text(user_text: str) -> str:
    return process_text_detailed(user_text).response


def process_text_detailed(user_text: str) -> ProcessResult:
    return _run_routing_policy(user_text)


def _run_routing_policy(user_text: str) -> ProcessResult:
    steps: tuple[RoutingStep, ...] = (
        RoutingStep("system_intent", _handle_system_intent),
        RoutingStep("pending_project_idea", _handle_pending_project_idea),
        RoutingStep("pending_confirmation", _handle_pending_confirmation),
        RoutingStep("active_game", _handle_active_game),
        RoutingStep("intent_parser", _handle_parsed_intent),
    )
    for step in steps:
        result = step.handler(user_text)
        if result is None:
            continue
        _log_routing_step(step.name, user_text, result.intent)
        return result
    # Defensive fallback: currently unreachable, but keeps the routing contract explicit.
    response = "Не удалось обработать команду. Попробуй еще раз."
    return ProcessResult(intent="unknown", response=response, role="chat_agent")


def _handle_system_intent(user_text: str) -> ProcessResult | None:
    system_intent = detect_system_intent(user_text)
    if system_intent is None:
        return None

    role = role_for_intent(system_intent.intent)
    response = route_intent(system_intent, user_text)
    log_interaction_event(
        "interaction",
        {
            "user_text": user_text,
            "intent": system_intent.intent,
            "role": role,
            "intent_data": system_intent.data,
            "response": response,
        },
    )
    return ProcessResult(intent=system_intent.intent, response=response, role=role)


def _handle_parsed_intent(user_text: str) -> ProcessResult | None:
    try:
        intent_result = parse_intent(user_text)
    except OllamaClientError:
        response = "Не удалось подключиться к Ollama. Проверь, что локальный сервер запущен."
        log_interaction_event(
            "orchestrator_error",
            {
                "user_text": user_text,
                "error_type": "ollama_unavailable",
                "response": response,
            },
        )
        return ProcessResult(intent="unknown", response=response, role="chat_agent")
    except Exception as exc:
        response = "Не удалось обработать команду. Попробуй еще раз."
        log_interaction_event(
            "orchestrator_error",
            {
                "user_text": user_text,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "response": response,
            },
        )
        return ProcessResult(intent="unknown", response=response, role="chat_agent")

    role = role_for_intent(intent_result.intent)
    response = route_intent(intent_result, user_text)
    handoff_responses = _run_handoffs(intent_result, user_text)
    if handoff_responses:
        response = _merge_handoff_responses(response, handoff_responses)
    log_interaction_event(
        "interaction",
        {
            "user_text": user_text,
            "intent": intent_result.intent,
            "role": role,
            "intent_data": intent_result.data,
            "response": response,
        },
    )
    return ProcessResult(
        intent=intent_result.intent,
        response=response,
        role=role,
        needs_followup=_should_follow_up(intent_result.intent, response),
    )


def _handle_pending_confirmation(user_text: str) -> ProcessResult | None:
    pending = confirmation_store.get()
    if pending is None:
        return None

    decision = classify_confirmation_reply(user_text)
    if decision is None:
        response = "Нужно коротко подтвердить: скажи да или нет."
        return ProcessResult(intent="unknown", response=response, role="chat_agent", needs_followup=True)

    confirmation_store.clear()
    if decision == "cancel":
        if pending.kind == "clear_user_profile":
            return ProcessResult(intent="unknown", response="Хорошо, не очищаю личную память.", role="profile_agent")
        if pending.kind == "os_action":
            return ProcessResult(intent="unknown", response="Хорошо, отменяю действие.", role="os_operator_agent")
        return ProcessResult(intent="unknown", response="Хорошо, не удаляю.", role="task_agent")

    if pending.kind == "delete_all_tasks":
        response = confirm_delete_all_tasks()
        return ProcessResult(intent="delete_tasks", response=response, role="task_agent")
    if pending.kind == "clear_user_profile":
        response = confirm_clear_user_profile()
        return ProcessResult(intent="forget_user_profile", response=response, role="profile_agent")
    if pending.kind == "os_action":
        response = confirm_os_action(pending.payload)
        return ProcessResult(intent="unknown", response=response, role="os_operator_agent")

    return ProcessResult(intent="unknown", response="Подтверждение сброшено.", role="chat_agent")


def _handle_pending_project_idea(user_text: str) -> ProcessResult | None:
    if not has_pending_project_idea_clarification():
        return None
    response = continue_project_idea_clarification(user_text)
    if not response:
        return None
    needs_followup = "?" in response or response.endswith("...")
    return ProcessResult(
        intent="analyze_project_idea_to_obsidian",
        response=response,
        role="note_agent",
        needs_followup=needs_followup,
    )


def _handle_active_game(user_text: str) -> ProcessResult | None:
    if game_store.get() is None:
        return None

    response = handle_active_game_turn(user_text)
    if response is None:
        return None
    return ProcessResult(intent="play_game", response=response, role="game_agent", needs_followup=True)


def _should_follow_up(intent: str, response: str) -> bool:
    if intent in {"chat", "play_game", "start_dictation_mode"}:
        return True
    if intent == "unknown" and response:
        return True
    return response.strip().endswith("?")


def _log_routing_step(step_name: str, user_text: str, resolved_intent: str) -> None:
    log_interaction_event(
        "routing_step",
        {
            "step": step_name,
            "user_text": user_text,
            "resolved_intent": resolved_intent,
        },
    )


def _run_handoffs(intent_result: IntentResult, user_text: str) -> list[tuple[str, str]]:
    handoff_intents = build_handoffs(intent_result, user_text)
    if not handoff_intents:
        return []

    results: list[tuple[str, str]] = []
    for handoff_intent in handoff_intents:
        try:
            handoff_response = route_intent(handoff_intent, user_text).strip()
        except Exception as exc:
            log_interaction_event(
                "handoff_error",
                {
                    "source_intent": intent_result.intent,
                    "handoff_intent": handoff_intent.intent,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            continue
        if not handoff_response:
            continue
        if handoff_response not in {resp for _, resp in results}:
            results.append((handoff_intent.intent, handoff_response))

    if results:
        log_interaction_event(
            "handoff",
            {
                "source_intent": intent_result.intent,
                "handoff_intents": [intent for intent, _ in results],
            },
        )
    return results


def _merge_handoff_responses(primary_response: str, handoff_responses: list[tuple[str, str]]) -> str:
    if not handoff_responses:
        return primary_response

    fragments: list[str] = [primary_response.strip()] if primary_response.strip() else []
    for intent, response in handoff_responses:
        if intent == "create_event":
            fragments.append(f"Дополнительно в календаре: {response}")
            continue
        if intent == "get_events":
            fragments.append(f"И по событиям: {response}")
            continue
        if intent == "get_tasks":
            fragments.append(f"И по задачам: {response}")
            continue
        fragments.append(response)

    return "\n".join(fragment for fragment in fragments if fragment)
