from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas import ChatRequest, ChatResponse
from core.orchestrator import process_text_detailed


router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    text = " ".join(payload.text.split())
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty.")
    result = process_text_detailed(text)
    return ChatResponse(
        intent=result.intent,
        response=result.response,
        needs_followup=result.needs_followup,
    )

