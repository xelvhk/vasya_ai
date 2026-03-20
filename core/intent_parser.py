from config.prompts import INTENT_PROMPT_TEMPLATE
from core.models import IntentResult
from services.ollama_client import generate
from utils.json_utils import extract_json

def parse_intent(user_text: str) -> IntentResult:
    prompt = INTENT_PROMPT_TEMPLATE.format(user_text=user_text)
    raw_response = generate(prompt)
    data = extract_json(raw_response)
    return IntentResult(**data)