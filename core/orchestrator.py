from core.intent_parser import parse_intent
from core.router import route_intent
from services.ollama_client import OllamaClientError

def process_text(user_text: str) -> str:
    try:
        intent_result = parse_intent(user_text)
    except OllamaClientError:
        return "Не удалось подключиться к Ollama. Проверь, что локальный сервер запущен."
    except Exception:
        return "Не удалось обработать команду. Попробуй еще раз."

    return route_intent(intent_result)
