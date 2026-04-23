from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Generator

from core.orchestrator import process_text_detailed
from utils.logger import log_interaction_event
from voice.backend_registry import get_tts_backend


@dataclass(frozen=True)
class PipelineEvent:
    type: str
    stage: str
    ts_ms: float
    data: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PipelineResult:
    intent: str
    response: str
    needs_followup: bool
    metrics: dict[str, float]


def run_text_pipeline(
    user_text: str,
    *,
    speak_response: bool = False,
    tts_backend_name: str = "default",
    speak_strategy: str = "full",
    should_stop: Callable[[], bool] | None = None,
) -> Generator[PipelineEvent, None, PipelineResult]:
    started = time.perf_counter()
    text = " ".join(str(user_text).split())
    if not text:
        raise ValueError("Text is empty.")

    yield _event("stage", "input_received", started, {"text": text})
    canceled = False

    if _should_stop(should_stop):
        canceled = True
        yield _event("stage", "pipeline_canceled", started, {"reason": "before_intent"})
        metrics = {
            "intent_ms": 0.0,
            "ttfr_ms": 0.0,
            "tts_start_ms": 0.0,
            "tts_ms": 0.0,
            "total_ms": round((time.perf_counter() - started) * 1000, 2),
            "cancelled": 1.0,
        }
        yield _event("done", "pipeline_done", started, {"metrics": metrics, "canceled": True})
        return PipelineResult(intent="canceled", response="", needs_followup=False, metrics=metrics)

    intent_started = time.perf_counter()
    result = process_text_detailed(text)
    intent_ms = (time.perf_counter() - intent_started) * 1000
    yield _event(
        "intent",
        "intent_resolved",
        started,
        {
            "intent": result.intent,
            "needs_followup": bool(result.needs_followup),
            "intent_ms": round(intent_ms, 2),
        },
    )

    if _should_stop(should_stop):
        canceled = True
        yield _event("stage", "pipeline_canceled", started, {"reason": "after_intent"})

    first_chunk_ms = (time.perf_counter() - started) * 1000
    chunks = _chunk_response(result.response)
    if not chunks:
        chunks = [result.response.strip()] if result.response.strip() else []

    if chunks and not canceled:
        yield _event(
            "stage",
            "response_started",
            started,
            {"chunks_total": len(chunks)},
        )

    strategy = str(speak_strategy or "full").strip().lower()
    if strategy not in {"full", "chunked"}:
        strategy = "full"

    tts_ms = 0.0
    tts_start_ms = 0.0
    tts_backend = None
    if speak_response and result.response.strip():
        tts_backend = get_tts_backend(tts_backend_name)

    for idx, chunk in enumerate(chunks):
        if canceled:
            break
        if _should_stop(should_stop):
            canceled = True
            yield _event(
                "stage",
                "pipeline_canceled",
                started,
                {"reason": "during_stream", "chunk_index": idx},
            )
            break
        if not chunk.strip():
            continue
        yield _event(
            "response_chunk",
            "response_stream",
            started,
            {
                "text": chunk,
                "index": idx,
                "is_final": idx == len(chunks) - 1,
            },
        )
        if speak_response and strategy == "chunked" and tts_backend is not None:
            chunk_start = time.perf_counter()
            if tts_start_ms <= 0.0:
                tts_start_ms = (chunk_start - started) * 1000
            tts_backend.speak(chunk)
            tts_ms += (time.perf_counter() - chunk_start) * 1000

    if chunks and not canceled:
        yield _event(
            "stage",
            "response_done",
            started,
            {
                "chunks_total": len(chunks),
                "chars_total": len(result.response.strip()),
            },
        )

    if speak_response and result.response.strip() and strategy == "full" and tts_backend is not None and not canceled:
        tts_started = time.perf_counter()
        tts_start_ms = (tts_started - started) * 1000
        tts_backend.speak(result.response)
        tts_ms += (time.perf_counter() - tts_started) * 1000

    if canceled and tts_backend is not None:
        try:
            tts_backend.stop()
        except Exception:
            pass

    if speak_response and tts_backend is not None:
        backend_name = getattr(tts_backend, "backend_id", None) or getattr(tts_backend, "name", "unknown")
        yield _event(
            "stage",
            "tts_done",
            started,
            {
                "tts_ms": round(tts_ms, 2),
                "tts_start_ms": round(tts_start_ms, 2),
                "tts_backend": backend_name,
                "speak_strategy": strategy,
            },
        )

    total_ms = (time.perf_counter() - started) * 1000
    metrics = {
        "intent_ms": round(intent_ms, 2),
        "ttfr_ms": round(first_chunk_ms, 2),
        "tts_start_ms": round(tts_start_ms, 2),
        "tts_ms": round(tts_ms, 2),
        "total_ms": round(total_ms, 2),
        "cancelled": 1.0 if canceled else 0.0,
    }
    yield _event("done", "pipeline_done", started, {"metrics": metrics, "canceled": canceled})

    log_interaction_event(
        "pipeline_text_perf",
        {
            "intent": result.intent,
            "needs_followup": bool(result.needs_followup),
            **metrics,
        },
    )
    return PipelineResult(
        intent="canceled" if canceled else result.intent,
        response=result.response,
        needs_followup=bool(result.needs_followup),
        metrics=metrics,
    )


def _event(event_type: str, stage: str, started: float, data: dict[str, object]) -> PipelineEvent:
    return PipelineEvent(
        type=event_type,
        stage=stage,
        ts_ms=round((time.perf_counter() - started) * 1000, 2),
        data=data,
    )


def _chunk_response(text: str) -> list[str]:
    normalized = str(text).strip()
    if not normalized:
        return []
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
    if parts:
        return parts
    return [normalized]


def _should_stop(should_stop: Callable[[], bool] | None) -> bool:
    if should_stop is None:
        return False
    try:
        return bool(should_stop())
    except Exception:
        return False
