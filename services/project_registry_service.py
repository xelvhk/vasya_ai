from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from config.projects import DEFAULT_PROJECTS, ProjectConfig


@dataclass(frozen=True)
class RegisteredProject:
    id: str
    name: str
    path: str
    kind: str
    priority: int
    exists: bool
    status: str
    warning: str | None = None


def list_project_registry(
    projects: Iterable[ProjectConfig] = DEFAULT_PROJECTS,
) -> list[RegisteredProject]:
    registered = [_to_registered_project(project) for project in projects]
    return sorted(registered, key=lambda project: (project.priority, project.name.lower(), project.id))


def _to_registered_project(project: ProjectConfig) -> RegisteredProject:
    path = project.path.expanduser()
    exists = path.exists()
    warning = None if exists else f"project path is missing: {path}"
    return RegisteredProject(
        id=project.id,
        name=project.name,
        path=str(path),
        kind=project.kind,
        priority=project.priority,
        exists=exists,
        status="OK" if exists else "WARN",
        warning=warning,
    )
