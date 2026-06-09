from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas import MorningBriefRequest
from services.morning_show_service import build_morning_brief


router = APIRouter(prefix="/v1/morning-brief", tags=["morning-brief"])


@router.post("")
def morning_brief(payload: MorningBriefRequest) -> dict:
    brief = build_morning_brief(
        save_markdown=payload.save_markdown,
        use_llm=payload.use_llm,
    )
    return brief.to_dict()
