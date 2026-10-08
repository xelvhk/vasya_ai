from unittest.mock import Mock, patch

from core.intent_parser import parse_intent
from services.ollama_client import generate


def test_generate_sends_requested_model_retention() -> None:
    response = Mock()
    response.json.return_value = {"response": "ok"}
    with patch("services.ollama_client.ensure_ollama_running"), patch(
        "services.ollama_client.requests.post", return_value=response
    ) as post:
        assert generate("hello", model="llama3", keep_alive="15m") == "ok"
    assert post.call_args.kwargs["json"]["keep_alive"] == "15m"


def test_intent_router_requests_retention_for_classification_model() -> None:
    with patch(
        "core.intent_parser.generate",
        return_value='{"intent":"create_event","data":{"title":"Встреча"}}',
    ) as model:
        result = parse_intent("Пожалуйста, запиши мне встречу с командой завтра")
    assert result.intent == "create_event"
    assert model.call_args.kwargs["keep_alive"] == "15m"
