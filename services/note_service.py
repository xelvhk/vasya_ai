from repositories.note_repository import NoteRepository


_note_repository = NoteRepository()


def create_note(content: str) -> dict:
    return _note_repository.create(content).model_dump()


def get_notes(limit: int = 10) -> list[dict]:
    return [note.model_dump() for note in _note_repository.list_recent(limit=limit)]
