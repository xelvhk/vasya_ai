from __future__ import annotations

from fastapi import APIRouter

from config.settings import TASKS_BACKEND, VASYA_API_AUTH_TOKEN, VASYA_API_REQUIRE_AUTH
from services.obsidian_service import resolve_obsidian_vault_path


router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready() -> dict:
    api_auth_ready = (not VASYA_API_REQUIRE_AUTH) or bool(VASYA_API_AUTH_TOKEN)

    obsidian_ready = True
    obsidian_error = ""
    if TASKS_BACKEND == "obsidian_daily":
        vault_path, error = resolve_obsidian_vault_path()
        obsidian_ready = vault_path is not None and not error
        obsidian_error = str(error or "")

    checks = {
        "api_auth": {
            "ok": api_auth_ready,
            "required": VASYA_API_REQUIRE_AUTH,
        },
        "tasks_backend": {
            "ok": True,
            "name": TASKS_BACKEND,
        },
        "obsidian_vault": {
            "ok": obsidian_ready,
            "required_for_backend": TASKS_BACKEND == "obsidian_daily",
            "error": obsidian_error,
        },
    }
    ready = bool(api_auth_ready and obsidian_ready)
    return {
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "checks": checks,
    }
