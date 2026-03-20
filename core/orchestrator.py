from core.intent_parser import parse_intent
from core.router import route_intent

def process_text(user_text: str) -> str:
    intent_result = parse_intent(user_text)
    return route_intent(intent_result)