from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from apps.api.deps import is_ws_authorized
from apps.api.rate_limit import (
    check_ws_message_rate_limit,
    register_ws_connection,
    resolve_client_id_from_websocket,
    unregister_ws_connection,
)
from apps.api.schemas import PipelineRequest, PipelineResponse
from services.benchmark_service import build_benchmark_snapshot, build_benchmark_text_report
from utils.logger import log_interaction_event
from voice.backend_registry import list_backend_registry
from voice.pipeline import run_text_pipeline


router = APIRouter(prefix="/v1", tags=["realtime"])


@router.get("/bench/voice")
def bench_voice(limit: int = 80, as_json: bool = False) -> dict[str, object]:
    if as_json:
        return {"ok": True, "data": build_benchmark_snapshot(limit=limit)}
    return {"ok": True, "text": build_benchmark_text_report(limit=limit)}


@router.get("/backends")
def list_backends() -> dict[str, object]:
    return {"ok": True, "registry": list_backend_registry()}


@router.post("/pipeline", response_model=PipelineResponse)
def pipeline(payload: PipelineRequest) -> PipelineResponse:
    text = " ".join(payload.text.split())
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty.")

    events = run_text_pipeline(
        text,
        speak_response=bool(payload.speak_response),
        tts_backend_name=str(payload.tts_backend or "default"),
        speak_strategy=str(payload.speak_strategy or "full"),
    )

    final_intent = "unknown"
    final_response = ""
    final_followup = False
    final_metrics: dict[str, float] = {}
    for event in events:
        if event.stage == "intent_resolved":
            final_intent = str(event.data.get("intent", "unknown"))
            final_followup = bool(event.data.get("needs_followup", False))
        if event.stage == "response_stream":
            final_response = f"{final_response} {str(event.data.get('text', '')).strip()}".strip()
        if event.stage == "pipeline_done":
            raw_metrics = event.data.get("metrics", {})
            if isinstance(raw_metrics, dict):
                final_metrics = {str(k): float(v) for k, v in raw_metrics.items()}

    return PipelineResponse(
        intent=final_intent,
        response=final_response,
        needs_followup=final_followup,
        metrics=final_metrics,
    )


@router.websocket("/ws/voice")
async def voice_ws(websocket: WebSocket) -> None:
    if not is_ws_authorized(websocket):
        await websocket.close(code=4401)
        return
    client_id = resolve_client_id_from_websocket(websocket)
    connection_decision = register_ws_connection(client_id)
    if not connection_decision.allowed:
        log_interaction_event(
            "api_rate_limited",
            {
                "scope": "ws_connection",
                "path": "/v1/ws/voice",
                "client_id": client_id,
                "retry_after_seconds": connection_decision.retry_after_seconds,
            },
        )
        await websocket.close(code=4429, reason="Rate limit exceeded")
        return

    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "type": "ready",
                "protocol": "vasya.voice.realtime.v1",
                "message": "Send JSON: {\"type\":\"text\",\"text\":\"...\",\"speak\":false}",
            }
        )
        while True:
            raw_message = await websocket.receive_text()
            message_decision = check_ws_message_rate_limit(client_id)
            if not message_decision.allowed:
                log_interaction_event(
                    "api_rate_limited",
                    {
                        "scope": "ws_message",
                        "path": "/v1/ws/voice",
                        "client_id": client_id,
                        "retry_after_seconds": message_decision.retry_after_seconds,
                    },
                )
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Rate limit exceeded. Please retry later.",
                        "retry_after_seconds": message_decision.retry_after_seconds,
                    }
                )
                await websocket.close(code=4429, reason="Rate limit exceeded")
                return
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = str(payload.get("type", "")).strip().lower()
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if msg_type != "text":
                await websocket.send_json({"type": "error", "message": "Unsupported message type"})
                continue

            text = " ".join(str(payload.get("text", "")).split())
            if not text:
                await websocket.send_json({"type": "error", "message": "Empty text"})
                continue

            speak_response = bool(payload.get("speak", False))
            tts_backend = str(payload.get("tts_backend", "default"))
            speak_strategy = str(payload.get("speak_strategy", "full"))
            for event in run_text_pipeline(
                text,
                speak_response=speak_response,
                tts_backend_name=tts_backend,
                speak_strategy=speak_strategy,
                ):
                    await websocket.send_json(event.to_dict())
    except WebSocketDisconnect:
        return
    finally:
        unregister_ws_connection(client_id)
