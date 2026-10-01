"""Write reviewed video transcripts to the indexed part of an Obsidian vault."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import quote

from services.allowed_knowledge_service import resolve_knowledge_vault_path
from services.video_analysis_service import VideoAnalysisError, extract_instagram_request


_VIDEO_ID = re.compile(r"^[0-9a-f]{64}$")
_MAX_NOTE_BYTES = 240_000


class VideoNoteError(ValueError):
    pass


@dataclass(frozen=True)
class SavedVideoNote:
    relative_path: str
    url: str


def save_video_note(
    *, video_id: str, source_url: str | None, summary: str,
    subtitle_srt: str, subtitle_origin: str, vault_path: Path | None = None,
) -> SavedVideoNote:
    if not _VIDEO_ID.fullmatch(video_id):
        raise VideoNoteError("Некорректный идентификатор видео.")
    if subtitle_origin not in {"original", "transcribed"}:
        raise VideoNoteError("Неизвестный источник субтитров.")
    if not subtitle_srt.strip():
        raise VideoNoteError("Нет расшифровки для сохранения.")
    if len(summary) > 5000 or len(subtitle_srt.encode("utf-8")) > 220_000:
        raise VideoNoteError("Расшифровка слишком велика для одной заметки.")

    canonical_url = None
    if source_url:
        try:
            canonical_url, _ = extract_instagram_request(source_url)
        except VideoAnalysisError as exc:
            raise VideoNoteError("Некорректная ссылка на источник видео.") from exc
        expected_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
        if expected_id != video_id:
            raise VideoNoteError("Идентификатор и ссылка на видео не совпадают.")

    vault = (vault_path or resolve_knowledge_vault_path()).expanduser()
    knowledge = vault / "30_Knowledge"
    folder = knowledge / "Video"
    if (
        not vault.is_dir() or vault.is_symlink()
        or not knowledge.is_dir() or knowledge.is_symlink()
        or folder.is_symlink()
    ):
        raise VideoNoteError("Разрешённая папка Obsidian недоступна.")
    vault_real = vault.resolve()
    if not knowledge.resolve().is_relative_to(vault_real):
        raise VideoNoteError("Папка Obsidian выходит за пределы vault.")
    try:
        folder.mkdir(exist_ok=True)
        if not folder.resolve().is_relative_to(knowledge.resolve()):
            raise VideoNoteError("Папка видео выходит за пределы vault.")
        target = folder / f"video-{video_id[:20]}.md"
        if target.is_symlink():
            raise VideoNoteError("Путь заметки занят ссылкой.")
        processed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        source_line = f"Источник: {canonical_url}" if canonical_url else f"Файл SHA-256: {video_id}"
        content = (
            f"# Видео {video_id[:12]}\n\n"
            f"{source_line}\n\n"
            f"Обработано: {processed_at}\n\n"
            f"Субтитры: {'оригинальные' if subtitle_origin == 'original' else 'локальная расшифровка'}\n\n"
            f"## Краткий ответ\n\n{summary.strip() or 'Без краткого ответа.'}\n\n"
            f"## Расшифровка с таймкодами\n\n{subtitle_srt.strip()}\n"
        )
        if len(content.encode("utf-8")) > _MAX_NOTE_BYTES:
            raise VideoNoteError("Расшифровка слишком велика для индекса знаний.")
        descriptor, temporary = tempfile.mkstemp(prefix=".video-note-", suffix=".tmp", dir=folder)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write(content)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError as exc:
        raise VideoNoteError("Не удалось сохранить заметку в Obsidian.") from exc
    relative_path = target.relative_to(vault).as_posix()
    url = (
        f"obsidian://open?vault={quote(vault.name, safe='')}"
        f"&file={quote(relative_path, safe='')}"
    )
    return SavedVideoNote(relative_path=relative_path, url=url)
