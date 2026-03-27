from config.settings import (
    OLLAMA_FAST_MODEL,
    OLLAMA_FAST_NUM_PREDICT,
    OLLAMA_FAST_TEMPERATURE,
    OLLAMA_FAST_THINK,
)
from config.prompts import INTENT_PROMPT_TEMPLATE
from core.models import IntentResult
from services.ollama_client import generate
from utils.json_utils import extract_json
from utils.system_intents import detect_system_intent


def parse_intent(user_text: str) -> IntentResult:
    system_intent = detect_system_intent(user_text)
    if system_intent is not None:
        return system_intent

    prompt = INTENT_PROMPT_TEMPLATE.format(user_text=user_text)
    raw_response = generate(
        prompt,
        model=OLLAMA_FAST_MODEL,
        think=OLLAMA_FAST_THINK,
        temperature=OLLAMA_FAST_TEMPERATURE,
        num_predict=OLLAMA_FAST_NUM_PREDICT,
    )
    data = extract_json(raw_response)
    return IntentResult(**data)
