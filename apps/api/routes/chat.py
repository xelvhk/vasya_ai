from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas import ChatRequest, ChatResponse
from core.orchestrator import process_text_detailed
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
    result = process_text_detailed(text)
    return ChatResponse(
        intent=result.intent,
        response=result.response,
        needs_followup=result.needs_followup,
    )
