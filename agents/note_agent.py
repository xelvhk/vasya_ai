from core.models import IntentResult
from services.note_service import create_note, get_notes
from utils.response_style import join_spoken_list


def handle_note_intent(intent_result: IntentResult) -> str:
    if intent_result.intent == "create_note":
        content = str(intent_result.data.get("content", "")).strip()
        if not content:
            return "Я не расслышал, что именно нужно запомнить."

        note = create_note(content)
        return f"Запомнил. Добавил заметку: {note['content']}."

    if intent_result.intent == "get_notes":
        notes = get_notes()
        if not notes:
            return "Пока ничего не записано в заметках."

        note_texts = [note["content"] for note in notes]
        count = len(note_texts)
        if count == 1:
            return f"Сейчас у меня записана одна заметка: {note_texts[0]}."
        if count <= 4:
            return f"Вот что я помню: {join_spoken_list(note_texts)}."
        preview = join_spoken_list(note_texts[:5])
        return f"Сейчас у меня записано {count} заметок. Из последних: {preview}."

    return "Не удалось обработать команду по заметкам."
