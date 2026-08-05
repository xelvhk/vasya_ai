from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


_CONTROL_CENTER_DIR = Path(__file__).resolve().parents[2] / "control_center"
_ASSET_DIR = _CONTROL_CENTER_DIR / "assets"

router = APIRouter(tags=["control-center"])


@router.get("/control-center", include_in_schema=False)
@router.get("/control-center/", include_in_schema=False)
def control_center_index() -> FileResponse:
    return FileResponse(_CONTROL_CENTER_DIR / "index.html", media_type="text/html")


@router.get("/control-center/assets/{asset_path:path}", include_in_schema=False)
def control_center_asset(asset_path: str) -> FileResponse:
    asset = (_ASSET_DIR / asset_path).resolve()
    if _ASSET_DIR.resolve() not in asset.parents or not asset.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(asset)
