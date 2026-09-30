from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from apps.api.schemas import ChatRequest, ChatResponse, ChatSource
from core.orchestrator import process_text_detailed
from services.project_registry_service import (
    build_project_status_summary,
    list_project_status,
    project_dashboard_target,
)
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
    result = process_text_detailed(text)
    return ChatResponse(
        intent=result.intent,
        response=result.response,
        needs_followup=result.needs_followup,
        navigation_target=getattr(result, "navigation_target", None),
    )
