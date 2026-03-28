from core.models import IntentResult
from services.game_service import start_game


def handle_game_intent(intent_result: IntentResult) -> str:
    game_name = intent_result.data.get("game")
    return start_game(game_name)
