from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Callable


@dataclass(frozen=True)
class RuntimeEnvResult:
    status: str
    message: str


def ensure_runtime_env_file(
    root: Path,
    *,
    template_path: Path | None = None,
    token_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32),
) -> RuntimeEnvResult:
    env_path = root / ".env"
    if env_path.exists():
        return RuntimeEnvResult("OK", ".env already exists; left unchanged")

    if template_path is not None and template_path.exists():
        content = build_env_from_template(
            template_path.read_text(encoding="utf-8"),
            token_factory=token_factory,
        )
    else:
        content = default_env_content(token_factory=token_factory)

    env_path.write_text(content, encoding="utf-8")
    env_path.chmod(0o600)
    return RuntimeEnvResult("OK", "created .env with generated VASYA_API_AUTH_TOKEN")


def build_env_from_template(
    template: str,
    *,
    token_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32),
) -> str:
    token = token_factory()
    lines = []
    token_seen = False
    for raw_line in template.splitlines():
        if raw_line.startswith("VASYA_API_AUTH_TOKEN="):
            lines.append(f"VASYA_API_AUTH_TOKEN={token}")
            token_seen = True
        else:
            lines.append(raw_line)
    if not token_seen:
        lines.append(f"VASYA_API_AUTH_TOKEN={token}")
    return "\n".join(lines).rstrip() + "\n"


def default_env_content(*, token_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32)) -> str:
    return (
        "APP_VERSION=0.6.0\n"
        "OLLAMA_MODEL=llama3\n"
        "GOOGLE_CALENDAR_ENABLED=false\n"
        f"VASYA_API_AUTH_TOKEN={token_factory()}\n"
        "VASYA_API_REQUIRE_AUTH=true\n"
    )
