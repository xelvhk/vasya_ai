from services.chat_service import generate_chat_reply


def handle_chat_intent(user_text: str) -> str:
    return generate_chat_reply(user_text)
