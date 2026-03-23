from core.intent_parser import parse_intent
from core.router import route_intent
from services.ollama_client import OllamaClientError
from utils.logger import log_interaction_event


def process_text(user_text: str) -> str:
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
        return response
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
        return response

    response = route_intent(intent_result)
    log_interaction_event(
        "interaction",
        {
            "user_text": user_text,
            "intent": intent_result.intent,
            "intent_data": intent_result.data,
            "response": response,
        },
    )
    return response
