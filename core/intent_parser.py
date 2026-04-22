from config.settings import (
    OLLAMA_FAST_MODEL,
    OLLAMA_FAST_NUM_PREDICT,
    OLLAMA_FAST_TEMPERATURE,
    OLLAMA_FAST_THINK,
)
from config.prompts import INTENT_PROMPT_TEMPLATE
from core.agent_policy import role_spec_block
from core.models import IntentResult
from services.ollama_client import generate
from utils.intent_fastpaths import detect_fast_intent
from utils.json_utils import extract_json
from utils.logger import log_voice_event
from utils.system_intents import detect_system_intent


def parse_intent(user_text: str) -> IntentResult:
    system_intent = detect_system_intent(user_text)
    if system_intent is not None:
        return system_intent

    fast_intent = detect_fast_intent(user_text)
    if fast_intent is not None:
        return fast_intent

    prompt = INTENT_PROMPT_TEMPLATE.format(
        user_text=user_text,
        router_role_spec=role_spec_block("router_agent"),
    )
    started = time.perf_counter()
    raw_response = generate(
        prompt,
        model=OLLAMA_FAST_MODEL,
        think=OLLAMA_FAST_THINK,
        temperature=OLLAMA_FAST_TEMPERATURE,
        num_predict=OLLAMA_FAST_NUM_PREDICT,
    )
    parse_ms = (time.perf_counter() - started) * 1000
    log_voice_event(f"intent_parse_ms={parse_ms:.0f} model={OLLAMA_FAST_MODEL}")
    data = extract_json(raw_response)
    return IntentResult(**data)
import time
