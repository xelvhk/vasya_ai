from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    intent: str
    response: str
    needs_followup: bool
    navigation_target: str | None = None


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
    navigation_target: str | None = None


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


class MemoryDigestRequest(BaseModel):
    date: str | None = Field(default=None, max_length=10)


class MorningBriefRequest(BaseModel):
    save_markdown: bool = True
    use_llm: bool = True


class ProjectStatusItem(BaseModel):
    id: str
    name: str
    path: str
    kind: str
    priority: int
    exists: bool
    status: str
    warning: str | None = None
    branch: str | None = None
    dirty: bool | None = None
    latest_commit: str | None = None
    next_action: str


class ProjectStatusResponse(BaseModel):
    items: list[ProjectStatusItem]


class ProjectRegistryItem(BaseModel):
    id: str
    name: str
    path: str
    kind: str
    priority: int
    enabled: bool


class ProjectRegistryResponse(BaseModel):
    items: list[ProjectRegistryItem]


class CreateProjectRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=4096)
    kind: str = Field(min_length=1, max_length=64)
    priority: int = Field(ge=0, le=100_000)
    enabled: bool = True


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    path: str | None = Field(default=None, min_length=1, max_length=4096)
    kind: str | None = Field(default=None, min_length=1, max_length=64)
    priority: int | None = Field(default=None, ge=0, le=100_000)
    enabled: bool | None = None
