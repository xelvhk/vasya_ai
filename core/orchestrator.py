from assistant.confirmations import classify_confirmation_reply, confirmation_store
from assistant.games import game_store
from agents.task_agent import confirm_delete_all_tasks
from services.game_service import handle_active_game_turn
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
    return ProcessResult(intent="unknown", response=response)


def _handle_system_intent(user_text: str) -> ProcessResult | None:
    system_intent = detect_system_intent(user_text)
    if system_intent is None:
        return None

    response = route_intent(system_intent, user_text)
    log_interaction_event(
        "interaction",
        {
            "user_text": user_text,
            "intent": system_intent.intent,
            "intent_data": system_intent.data,
            "response": response,
        },
    )
    return ProcessResult(intent=system_intent.intent, response=response)


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
        return ProcessResult(intent="unknown", response=response)
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
        return ProcessResult(intent="unknown", response=response)

    response = route_intent(intent_result, user_text)
    log_interaction_event(
        "interaction",
        {
            "user_text": user_text,
            "intent": intent_result.intent,
            "intent_data": intent_result.data,
            "response": response,
        },
    )
    return ProcessResult(
        intent=intent_result.intent,
        response=response,
        needs_followup=_should_follow_up(intent_result.intent, response),
    )


def _handle_pending_confirmation(user_text: str) -> ProcessResult | None:
    pending = confirmation_store.get()
    if pending is None:
        return None

    decision = classify_confirmation_reply(user_text)
    if decision is None:
        response = "Нужно коротко подтвердить: скажи да или нет."
        return ProcessResult(intent="unknown", response=response, needs_followup=True)

    confirmation_store.clear()
    if decision == "cancel":
        return ProcessResult(intent="unknown", response="Хорошо, не удаляю.")

    if pending.kind == "delete_all_tasks":
        response = confirm_delete_all_tasks()
        return ProcessResult(intent="delete_tasks", response=response)

    return ProcessResult(intent="unknown", response="Подтверждение сброшено.")


def _handle_active_game(user_text: str) -> ProcessResult | None:
    if game_store.get() is None:
        return None

    response = handle_active_game_turn(user_text)
    if response is None:
        return None
    return ProcessResult(intent="play_game", response=response, needs_followup=True)


def _should_follow_up(intent: str, response: str) -> bool:
    if intent in {"chat", "play_game"}:
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
