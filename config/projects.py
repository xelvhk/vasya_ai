from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class ProjectConfig:
    id: str
    name: str
    path: Path
    kind: str
    priority: int


_HOME = Path.home()

DEFAULT_PROJECTS: tuple[ProjectConfig, ...] = ()

PERSONAL_PROJECT_PRESETS: tuple[ProjectConfig, ...] = (
    ProjectConfig(
        id="ai_pal",
        name="Vasya AI",
        path=_HOME / "ai_pal",
        kind="python_desktop",
        priority=10,
    ),
    ProjectConfig(
        id="portfolio",
        name="Portfolio",
        path=_HOME / "portfolio",
        kind="web",
        priority=20,
    ),
    ProjectConfig(
        id="ai_twin",
        name="AI Twin",
        path=_HOME / "ai_twin",
        kind="ai_app",
        priority=30,
    ),
    ProjectConfig(
        id="ai_predictor",
        name="AI Predictor",
        path=_HOME / "ai_predictor",
        kind="ai_app",
        priority=40,
    ),
    ProjectConfig(
        id="document_ops_ai",
        name="Document Ops AI",
        path=_HOME / "document_ops_ai",
        kind="document_ai",
        priority=50,
    ),
    ProjectConfig(
        id="onboardica",
        name="Onboardica",
        path=_HOME / "onboardica",
        kind="product",
        priority=60,
    ),
)


def configured_project_configs(
    *,
    include_personal_presets: bool | None = None,
) -> tuple[ProjectConfig, ...]:
    if include_personal_presets is None:
        include_personal_presets = _env_flag("VASYA_PROJECT_OS_INCLUDE_PERSONAL_DEFAULTS")
    if include_personal_presets:
        return PERSONAL_PROJECT_PRESETS
    return DEFAULT_PROJECTS


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
