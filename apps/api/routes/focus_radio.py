"""Control the radio owned by the local desktop widget."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from config.settings import APP_PATHS
from services.focus_radio_bridge import enqueue_command, read_status


router = APIRouter(prefix="/v1/focus-radio", tags=["focus-radio"])


class RadioCommand(BaseModel):
    action: Literal["play", "pause", "mode", "volume"]
    mode: Literal["warm", "rain", "night", "pulse", "mix"] | None = None
    volume: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def require_value(self):
        if self.action == "mode" and self.mode is None:
            raise ValueError("mode is required")
        if self.action == "volume" and self.volume is None:
            raise ValueError("volume is required")
        return self


@router.get("")
def get_focus_radio() -> dict:
    return read_status(APP_PATHS.data_dir)


@router.post("", status_code=202)
def control_focus_radio(command: RadioCommand) -> dict:
    if not read_status(APP_PATHS.data_dir)["available"]:
        raise HTTPException(status_code=503, detail="Виджет Васи не запущен на этом компьютере.")
    enqueue_command(APP_PATHS.data_dir, command.model_dump(exclude_none=True))
    return {"queued": True}
