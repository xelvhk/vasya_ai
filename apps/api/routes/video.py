"""Authenticated raw upload for the local video agent."""

from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import unquote

from fastapi import APIRouter, Header, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from apps.api.schemas import ChatResponse, VideoSaveRequest, VideoSaveResponse
from services.video_analysis_service import (
    ALLOWED_MEDIA_EXTENSIONS, MAX_VIDEO_BYTES, VideoAnalysisError, analyze_media, render_srt,
)
from services.video_note_service import VideoNoteError, save_video_note


router = APIRouter(prefix="/v1/video", tags=["video"])


@router.post("/upload", response_model=ChatResponse)
async def upload_video(
    request: Request,
    extension: str = Header(alias="x-video-extension"),
    encoded_question: str = Header(default="", alias="x-video-question"),
) -> ChatResponse:
    suffix = "." + extension.lower().strip()
    if suffix not in ALLOWED_MEDIA_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Поддерживаются MP4, MOV, WebM и MKV.")
    question = unquote(encoded_question).strip()
    if len(question) > 500:
        raise HTTPException(status_code=422, detail="Вопрос слишком длинный.")
    with TemporaryDirectory(prefix="vasya-video-") as directory:
        path = Path(directory) / f"input{suffix}"
        size = 0
        content_hash = hashlib.sha256()
        with path.open("wb") as destination:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_VIDEO_BYTES:
                    raise HTTPException(status_code=413, detail="Видео больше 100 МиБ.")
                destination.write(chunk)
                content_hash.update(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Видео пустое.")
        try:
            analysis = await run_in_threadpool(analyze_media, path, question=question)
        except VideoAnalysisError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return ChatResponse(
        intent="video_analysis", response=analysis.response,
        needs_followup=False, sources=[],
        subtitle_srt=render_srt(analysis.segments), subtitle_origin=analysis.subtitle_origin,
        video_id=content_hash.hexdigest(),
    )


@router.post("/save-note", response_model=VideoSaveResponse)
def save_video_note_route(payload: VideoSaveRequest) -> VideoSaveResponse:
    try:
        saved = save_video_note(
            video_id=payload.video_id, source_url=payload.source_url,
            summary=payload.summary, subtitle_srt=payload.subtitle_srt,
            subtitle_origin=payload.subtitle_origin,
        )
    except VideoNoteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VideoSaveResponse(relative_path=saved.relative_path, url=saved.url)
