from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from config.projects import ProjectConfig


_PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_MISSING = object()


class ProjectRegistryFormatError(ValueError):
    """Raised when a registry file cannot be read without risking data loss."""


class ProjectAlreadyExistsError(ValueError):
    """Raised when a project id is already present in the registry."""


class ProjectNotFoundError(KeyError):
    """Raised when a requested project id is not present in the registry."""


@dataclass(frozen=True)
class UserProject:
    id: str
    name: str
    path: str
    kind: str
    priority: int
    enabled: bool = True

    def to_project_config(self) -> ProjectConfig:
        return ProjectConfig(
            id=self.id,
            name=self.name,
            path=Path(self.path),
            kind=self.kind,
            priority=self.priority,
        )


class ProjectRegistryStore:
    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()

    def list(self, *, include_disabled: bool = False) -> list[UserProject]:
        projects = self._load()
        if not include_disabled:
            projects = [project for project in projects if project.enabled]
        return sorted(projects, key=lambda item: (item.priority, item.name.lower(), item.id))

    def add(self, project: UserProject) -> UserProject:
        normalized = _validate_project(project)
        projects = self._load()
        if any(item.id == normalized.id for item in projects):
            raise ProjectAlreadyExistsError(normalized.id)
        projects.append(normalized)
        self._save(projects)
        return normalized

    def update(
        self,
        project_id: str,
        *,
        name: str | object = _MISSING,
        path: str | Path | object = _MISSING,
        kind: str | object = _MISSING,
        priority: int | object = _MISSING,
        enabled: bool | object = _MISSING,
    ) -> UserProject:
        projects = self._load()
        for index, current in enumerate(projects):
            if current.id != project_id:
                continue
            candidate = replace(
                current,
                name=current.name if name is _MISSING else name,
                path=current.path if path is _MISSING else str(path),
                kind=current.kind if kind is _MISSING else kind,
                priority=current.priority if priority is _MISSING else priority,
                enabled=current.enabled if enabled is _MISSING else enabled,
            )
            normalized = _validate_project(candidate)
            projects[index] = normalized
            self._save(projects)
            return normalized
        raise ProjectNotFoundError(project_id)

    def remove(self, project_id: str) -> UserProject:
        projects = self._load()
        for index, project in enumerate(projects):
            if project.id == project_id:
                removed = projects.pop(index)
                self._save(projects)
                return removed
        raise ProjectNotFoundError(project_id)

    def export(self, destination: str | Path) -> Path:
        destination_path = Path(destination).expanduser()
        self._write_payload(destination_path, self._load())
        return destination_path

    def _load(self) -> list[UserProject]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProjectRegistryFormatError("project registry is not valid JSON") from exc
        except OSError as exc:
            raise ProjectRegistryFormatError("project registry could not be read") from exc
        if not isinstance(payload, dict):
            raise ProjectRegistryFormatError("project registry root must be an object")
        if payload.get("version") != self.SCHEMA_VERSION:
            raise ProjectRegistryFormatError("unsupported project registry version")
        raw_projects = payload.get("projects")
        if not isinstance(raw_projects, list):
            raise ProjectRegistryFormatError("project registry projects must be a list")

        projects: list[UserProject] = []
        seen_ids: set[str] = set()
        for raw_project in raw_projects:
            if not isinstance(raw_project, dict):
                raise ProjectRegistryFormatError("project registry entry must be an object")
            try:
                project = _validate_project(UserProject(**raw_project))
            except (TypeError, ValueError) as exc:
                raise ProjectRegistryFormatError("project registry contains an invalid entry") from exc
            if project.id in seen_ids:
                raise ProjectRegistryFormatError(f"duplicate project id: {project.id}")
            seen_ids.add(project.id)
            projects.append(project)
        return projects

    def _save(self, projects: list[UserProject]) -> None:
        self._write_payload(self.path, projects)

    def _write_payload(self, path: Path, projects: list[UserProject]) -> None:
        payload = {
            "version": self.SCHEMA_VERSION,
            "projects": [asdict(project) for project in projects],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                temporary_path = Path(handle.name)
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()


def _validate_project(project: UserProject) -> UserProject:
    project_id = _clean_text(project.id, field="id", maximum=64)
    if not _PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError("project id must use lowercase letters, numbers, '-' or '_'")
    name = _clean_text(project.name, field="name", maximum=120)
    kind = _clean_text(project.kind, field="kind", maximum=64)
    raw_path = _clean_text(project.path, field="path", maximum=4096)
    if "\x00" in raw_path:
        raise ValueError("project path contains a null byte")
    normalized_path = Path(raw_path).expanduser()
    if not normalized_path.is_absolute():
        raise ValueError("project path must be absolute or start with '~'")
    if isinstance(project.priority, bool) or not isinstance(project.priority, int):
        raise ValueError("project priority must be an integer")
    if not 0 <= project.priority <= 100_000:
        raise ValueError("project priority must be between 0 and 100000")
    if not isinstance(project.enabled, bool):
        raise ValueError("project enabled must be a boolean")
    return UserProject(
        id=project_id,
        name=name,
        path=str(normalized_path),
        kind=kind,
        priority=project.priority,
        enabled=project.enabled,
    )


def _clean_text(value: Any, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"project {field} must be text")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"project {field} must not be empty")
    if len(cleaned) > maximum:
        raise ValueError(f"project {field} is too long")
    return cleaned
