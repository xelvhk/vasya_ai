from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Iterable

from config.projects import ProjectConfig, configured_project_configs


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


@dataclass(frozen=True)
class ProjectStatus:
    id: str
    name: str
    path: str
    kind: str
    priority: int
    exists: bool
    status: str
    warning: str | None
    branch: str | None
    dirty: bool | None
    latest_commit: str | None
    next_action: str


def list_project_registry(
    projects: Iterable[ProjectConfig] | None = None,
) -> list[RegisteredProject]:
    if projects is None:
        projects = configured_project_configs()
    registered = [_to_registered_project(project) for project in projects]
    return sorted(registered, key=lambda project: (project.priority, project.name.lower(), project.id))


def list_project_status(
    projects: Iterable[ProjectConfig] | None = None,
) -> list[ProjectStatus]:
    return [_to_project_status(project) for project in list_project_registry(projects)]


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


def _to_project_status(project: RegisteredProject) -> ProjectStatus:
    if not project.exists:
        return ProjectStatus(
            id=project.id,
            name=project.name,
            path=project.path,
            kind=project.kind,
            priority=project.priority,
            exists=False,
            status="WARN",
            warning=project.warning,
            branch=None,
            dirty=None,
            latest_commit=None,
            next_action="Add or fix the project path.",
        )

    branch, branch_error = _git_output(project.path, ["rev-parse", "--abbrev-ref", "HEAD"])
    dirty_output, dirty_error = _git_output(project.path, ["status", "--porcelain"])
    latest_commit, commit_error = _git_output(project.path, ["log", "-1", "--pretty=format:%h %s"])
    git_error = branch_error or dirty_error or commit_error

    return ProjectStatus(
        id=project.id,
        name=project.name,
        path=project.path,
        kind=project.kind,
        priority=project.priority,
        exists=True,
        status="WARN" if git_error else "OK",
        warning=f"git metadata unavailable: {git_error}" if git_error else project.warning,
        branch=branch if not branch_error else None,
        dirty=bool(dirty_output) if not dirty_error else None,
        latest_commit=latest_commit if not commit_error else None,
        next_action="Review project status.",
    )


def _git_output(path: str, args: list[str]) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=path,
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    return result.stdout.strip(), None
