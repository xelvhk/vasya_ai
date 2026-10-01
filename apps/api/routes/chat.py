from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from apps.api.schemas import ChatRequest, ChatResponse, ChatSource
from core.orchestrator import process_text_detailed
from services.allowed_knowledge_index_service import search_indexed_notes
from services.grounded_knowledge_answer_service import answer_from_hits
from services.project_registry_service import (
    build_project_status_summary,
    list_project_status,
    project_dashboard_target,
)
from services.video_analysis_service import VideoAnalysisError, analyze_instagram_request, render_srt
from utils.logger import log_interaction_event


router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    text = " ".join(payload.text.split())
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty.")
    log_interaction_event(
        "routing_step",
        {
            "step": "api_chat_inbound",
            "user_text": text,
        },
    )
    if payload.agent == "projects":
        statuses = list_project_status()
        observed_at = datetime.now(timezone.utc)
        return ChatResponse(
            intent="project_status_summary",
            response=build_project_status_summary(statuses),
            needs_followup=not statuses,
            sources=[
                ChatSource(
                    id=f"project:{project.id}",
                    title=project.name,
                    url=project_dashboard_target(project.id),
                    observed_at=observed_at,
                )
                for project in statuses[:4]
            ],
        )
    if payload.agent == "knowledge":
        result = search_indexed_notes(text)
        if result.error:
            return ChatResponse(
                intent="knowledge_search",
                response=result.error,
                needs_followup=True,
            )
        freshness = (
            f"Источник сейчас недоступен; показываю снимок от {result.observed_at:%d.%m.%Y %H:%M} UTC.\n"
            if result.stale and result.observed_at
            else ""
        )
        if not result.hits:
            return ChatResponse(
                intent="knowledge_search",
                response=freshness + "Не нашёл подтверждения в разрешённых папках Obsidian. Уточните запрос.",
                needs_followup=True,
            )
        observed_at = result.observed_at or datetime.now(timezone.utc)
        excerpts = [
            f"[{index}] {hit.title}: {hit.excerpt or 'Совпадение найдено в заголовке.'}"
            for index, hit in enumerate(result.hits, start=1)
        ]
        grounded_answer = answer_from_hits(text, result.hits)
        return ChatResponse(
            intent="knowledge_answer" if grounded_answer else "knowledge_search",
            response=freshness + (
                grounded_answer if grounded_answer else
                "Не удалось подготовить ответ с проверенной цитатой. Найденные фрагменты:\n"
                + "\n".join(excerpts)
            ),
            needs_followup=False,
            sources=[
                ChatSource(
                    id=f"obsidian:{hit.relative_path}",
                    title=hit.relative_path,
                    url=hit.url,
                    observed_at=observed_at,
                    modified_at=hit.modified_at,
                )
                for hit in result.hits
            ],
        )
    if payload.agent == "video":
        try:
            analysis = analyze_instagram_request(text)
        except VideoAnalysisError as exc:
            return ChatResponse(
                intent="video_analysis", response=str(exc), needs_followup=True,
            )
        return ChatResponse(
            intent="video_analysis", response=analysis.response, needs_followup=False,
            subtitle_srt=render_srt(analysis.segments), subtitle_origin=analysis.subtitle_origin,
            sources=[ChatSource(
                id=f"instagram:{analysis.source_url.rsplit('/', 2)[-2]}",
                title="Видео Instagram", url=analysis.source_url,
                observed_at=datetime.now(timezone.utc),
            )] if analysis.source_url else [],
        )
    result = process_text_detailed(text)
    return ChatResponse(
        intent=result.intent,
        response=result.response,
        needs_followup=result.needs_followup,
        navigation_target=getattr(result, "navigation_target", None),
    )
