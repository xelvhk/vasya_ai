from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Response, status

from apps.api.schemas import (
    CreateProjectRequest,
    ProjectRegistryItem,
    ProjectRegistryResponse,
    ProjectStatusResponse,
    UpdateProjectRequest,
)
from config.settings import PROJECT_REGISTRY_FILE
from services.project_registry_service import list_project_status
from services.project_registry_store import (
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    ProjectRegistryFormatError,
    ProjectRegistryStore,
    UserProject,
)


router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.get("/status", response_model=ProjectStatusResponse)
def get_project_status() -> ProjectStatusResponse:
    return ProjectStatusResponse(items=[asdict(project) for project in list_project_status()])


@router.get("", response_model=ProjectRegistryResponse)
def get_project_registry(include_disabled: bool = True) -> ProjectRegistryResponse:
    projects = _load_projects(include_disabled=include_disabled)
    return ProjectRegistryResponse(items=[_project_item(project) for project in projects])


@router.post("", response_model=ProjectRegistryItem, status_code=status.HTTP_201_CREATED)
def create_project(request: CreateProjectRequest) -> ProjectRegistryItem:
    try:
        project = _registry_store().add(UserProject(**request.model_dump()))
    except ProjectAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail="Project id already exists.") from exc
    except ProjectRegistryFormatError as exc:
        raise _registry_format_error() from exc
    except ValueError as exc:
        raise _project_validation_error(exc) from exc
    return _project_item(project)


@router.patch("/{project_id}", response_model=ProjectRegistryItem)
def update_project(project_id: str, request: UpdateProjectRequest) -> ProjectRegistryItem:
    changes = request.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one project field is required.")
    try:
        project = _registry_store().update(project_id, **changes)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except ProjectRegistryFormatError as exc:
        raise _registry_format_error() from exc
    except ValueError as exc:
        raise _project_validation_error(exc) from exc
    return _project_item(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str) -> Response:
    try:
        _registry_store().remove(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except ProjectRegistryFormatError as exc:
        raise _registry_format_error() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _load_projects(*, include_disabled: bool) -> list[UserProject]:
    try:
        return _registry_store().list(include_disabled=include_disabled)
    except ProjectRegistryFormatError as exc:
        raise _registry_format_error() from exc


def _registry_store() -> ProjectRegistryStore:
    return ProjectRegistryStore(PROJECT_REGISTRY_FILE)


def _project_item(project: UserProject) -> ProjectRegistryItem:
    return ProjectRegistryItem(**asdict(project))


def _registry_format_error() -> HTTPException:
    return HTTPException(
        status_code=500,
        detail="Project registry could not be read safely.",
    )


def _project_validation_error(exc: ValueError) -> HTTPException:
    if str(exc) == "project path must be absolute or start with '~'":
        detail = "Project path must be absolute."
    else:
        detail = "Project data is invalid."
    return HTTPException(status_code=422, detail=detail)
