from core.models import IntentResult
from services.game_service import repeat_last_game, start_game


def handle_game_intent(intent_result: IntentResult) -> str:
    game_name = intent_result.data.get("game")
    if game_name == "__repeat_last__":
        return repeat_last_game()
    return start_game(game_name)
