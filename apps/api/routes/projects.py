from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from apps.api.schemas import ProjectStatusResponse
from services.project_registry_service import list_project_status


router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.get("/status", response_model=ProjectStatusResponse)
def get_project_status() -> ProjectStatusResponse:
    return ProjectStatusResponse(items=[asdict(project) for project in list_project_status()])
