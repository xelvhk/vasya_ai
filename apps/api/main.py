from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.orchestrator import process_text_detailed
from services.calendar_service import create_event, get_events
from services.note_service import create_note, get_notes
from services.task_service import create_task, get_tasks
from services.voice_recovery_service import apply_voice_auto_tune_from_metrics, run_voice_mic_test


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    intent: str
    response: str
    needs_followup: bool


class CreateTaskRequest(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    datetime: str | None = None


class CreateNoteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CreateEventRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    datetime: str | None = None


app = FastAPI(
    title="Vasya API",
    version="0.1.0",
    description="HTTP gateway for desktop/mobile clients over Vasya core logic.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat", response_model=ChatResponse)
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


@app.get("/v1/tasks")
def list_tasks(date: str | None = None) -> dict:
    return {"items": get_tasks(filter_date=date)}


@app.post("/v1/tasks")
def add_task(payload: CreateTaskRequest) -> dict:
    task = create_task(payload.task.strip(), dt=payload.datetime)
    return {"item": task}


@app.get("/v1/notes")
def list_notes(limit: int = 20) -> dict:
    safe_limit = min(100, max(1, int(limit)))
    return {"items": get_notes(limit=safe_limit)}


@app.post("/v1/notes")
def add_note(payload: CreateNoteRequest) -> dict:
    note = create_note(payload.content.strip())
    return {"item": note}


@app.get("/v1/events")
def list_events(date: str | None = None) -> dict:
    return get_events(filter_date=date)


@app.post("/v1/events")
def add_event(payload: CreateEventRequest) -> dict:
    event = create_event(payload.title.strip(), dt=payload.datetime)
    return {"item": event}


@app.post("/v1/recovery/mic-test")
def mic_test() -> dict[str, str]:
    return {"message": run_voice_mic_test(duration_seconds=2.0)}


@app.post("/v1/recovery/auto-tune")
def auto_tune_voice() -> dict[str, str]:
    return {"message": apply_voice_auto_tune_from_metrics(limit=40)}

