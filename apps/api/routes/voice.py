"""Authenticated local transcription for short voice messages."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from voice.stt import transcribe


router = APIRouter(prefix="/v1/voice", tags=["voice"])
MAX_VOICE_BYTES = 20 * 1024 * 1024
MAX_VOICE_SECONDS = 300
VOICE_EXTENSIONS = frozenset({"ogg", "mp3", "m4a"})


class VoiceTranscript(BaseModel):
    text: str
    language: str | None = None


def _probe_audio_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=20, check=True,
        )
        data = json.loads(result.stdout)
        if not any(stream.get("codec_type") == "audio" for stream in data.get("streams", [])):
            raise ValueError("No audio stream")
        duration = float(data["format"]["duration"])
        if not 0 < duration < float("inf"):
            raise ValueError("Invalid duration")
        return duration
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail="Не удалось прочитать аудио.") from exc


@router.post("/transcribe", response_model=VoiceTranscript)
async def transcribe_voice(
    request: Request,
    extension: str = Header(alias="x-voice-extension"),
) -> VoiceTranscript:
    suffix = extension.lower().strip()
    if suffix not in VOICE_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Поддерживаются OGG, MP3 и M4A.")
    with TemporaryDirectory(prefix="vasya-voice-") as directory:
        path = Path(directory) / f"input.{suffix}"
        size = 0
        with path.open("wb") as destination:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_VOICE_BYTES:
                    raise HTTPException(status_code=413, detail="Аудио больше 20 МиБ.")
                destination.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Аудио пустое.")
        duration = await run_in_threadpool(_probe_audio_duration, path)
        if duration > MAX_VOICE_SECONDS:
            raise HTTPException(status_code=413, detail="Аудио длиннее 5 минут.")
        try:
            result = await run_in_threadpool(transcribe, str(path))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Расшифровка недоступна.") from exc
    if not result.text.strip():
        raise HTTPException(status_code=422, detail="Речь не распознана.")
    return VoiceTranscript(text=result.text.strip(), language=result.language)
