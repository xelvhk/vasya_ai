from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectConfig:
    id: str
    name: str
    path: Path
    kind: str
    priority: int


_HOME = Path.home()

DEFAULT_PROJECTS: tuple[ProjectConfig, ...] = (
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
