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
    raw_response = generate(prompt)
    data = extract_json(raw_response)
    return IntentResult(**data)
