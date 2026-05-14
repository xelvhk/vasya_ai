from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    intent: str
    response: str
    needs_followup: bool


class PipelineRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    speak_response: bool = False
    tts_backend: str = "default"
    speak_strategy: str = "full"


class PipelineResponse(BaseModel):
    intent: str
    response: str
    needs_followup: bool
    metrics: dict[str, float]


class CreateTaskRequest(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    datetime: str | None = None


class CreateNoteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CreateEventRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    datetime: str | None = None


class MemorySyncRequest(BaseModel):
    source: str = Field(pattern="^(github|notion|obsidian|all)$")
    force: bool = False
    repo: str | None = Field(default=None, max_length=240)
    page_id: str | None = Field(default=None, max_length=240)
