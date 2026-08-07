from __future__ import annotations

from dataclasses import dataclass
import re
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


def build_project_status_summary(
    projects: Iterable[ProjectStatus] | None = None,
) -> str:
    statuses = list(projects) if projects is not None else list_project_status()
    if not statuses:
        return "В Vasya Project OS пока нет добавленных проектов."

    fragments = [_project_summary_fragment(project) for project in statuses[:4]]
    if len(statuses) > 4:
        fragments.append(f"ещё проектов: {len(statuses) - 4}")
    next_action = statuses[0].next_action.strip()
    summary = f"По проектам: {'; '.join(fragments)}."
    if next_action:
        summary = f"{summary} Ближайший шаг: {next_action}"
    return summary


def resolve_project_reference(
    reference: str,
    projects: Iterable[ProjectConfig] | None = None,
) -> RegisteredProject | None:
    normalized_reference = _normalize_project_reference(reference)
    if not normalized_reference:
        return None
    matches = [
        project
        for project in list_project_registry(projects)
        if normalized_reference
        in {
            _normalize_project_reference(project.id),
            _normalize_project_reference(project.name),
        }
    ]
    return matches[0] if len(matches) == 1 else None


def project_dashboard_target(project_id: str) -> str:
    normalized_id = re.sub(r"[^a-zA-Z0-9_-]", "", project_id.strip())
    return f"/control-center#project-{normalized_id}"


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


def _project_summary_fragment(project: ProjectStatus) -> str:
    if project.status != "OK" or not project.exists:
        state = "требует внимания"
    elif project.dirty:
        branch = project.branch or "ветка не определена"
        state = f"{branch}, есть незакоммиченные изменения"
    elif project.branch:
        state = f"{project.branch}, чисто"
    else:
        state = "статус доступен"
    return f"{project.name} — {state}"


def _normalize_project_reference(value: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", "", value.strip().lower())


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
