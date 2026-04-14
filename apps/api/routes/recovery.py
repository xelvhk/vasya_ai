from __future__ import annotations

from fastapi import APIRouter

from services.voice_recovery_service import apply_voice_auto_tune_from_metrics, run_voice_mic_test


router = APIRouter(prefix="/v1/recovery", tags=["recovery"])


@router.post("/mic-test")
def mic_test() -> dict[str, str]:
    return {"message": run_voice_mic_test(duration_seconds=2.0)}


@router.post("/auto-tune")
def auto_tune_voice() -> dict[str, str]:
    return {"message": apply_voice_auto_tune_from_metrics(limit=40)}

