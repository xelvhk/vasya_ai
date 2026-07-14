from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from config.settings import AVATAR_CUSTOM_SKIN_FILE, AVATAR_PACK_SKINS, AVATAR_SKIN
except ModuleNotFoundError as exc:
    if exc.name != "config":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from config.settings import AVATAR_CUSTOM_SKIN_FILE, AVATAR_PACK_SKINS, AVATAR_SKIN


AVATAR_SKINS = {
    "classic": {
        "label": "Классический",
        "motion_speed": 1.0,
        "motion_bob": 1.0,
        "glow_alpha": 1.0,
        "body_top": "#4f86ff",
        "body_mid": "#224eb6",
        "body_bottom": "#08153b",
        "rim": "#6fe3ff",
        "face_center": "#ffffff",
        "face_edge": "#cad8f2",
        "eye_top": "#2c56be",
        "eye_mid": "#122869",
        "eye_bottom": "#071131",
        "mouth": "#1e2c63",
        "tuft": "#2e5fe0",
        "cheek": "#7ad6ff",
        "glow_idle": "#4f8fff",
        "glow_listening": "#3ec8ff",
        "glow_thinking": "#6fa8ff",
        "glow_speaking": "#5b7cff",
        "glow_error": "#ff6b6b",
    },
    "soft": {
        "label": "Мягкий",
        "motion_speed": 0.92,
        "motion_bob": 0.88,
        "glow_alpha": 0.92,
        "body_top": "#71b4ff",
        "body_mid": "#3f78d8",
        "body_bottom": "#13285f",
        "rim": "#a8ecff",
        "face_center": "#fffdfd",
        "face_edge": "#dbe6fb",
        "eye_top": "#4f7be3",
        "eye_mid": "#274391",
        "eye_bottom": "#10214f",
        "mouth": "#29407d",
        "tuft": "#5b8ef2",
        "cheek": "#a4e4ff",
        "glow_idle": "#74b8ff",
        "glow_listening": "#69dcff",
        "glow_thinking": "#8dbbff",
        "glow_speaking": "#7d96ff",
        "glow_error": "#ff8f95",
    },
    "sunset": {
        "label": "Теплый",
        "motion_speed": 0.96,
        "motion_bob": 0.95,
        "glow_alpha": 1.08,
        "body_top": "#ff9f6e",
        "body_mid": "#d95f64",
        "body_bottom": "#4b2048",
        "rim": "#ffd0a3",
        "face_center": "#fff8f3",
        "face_edge": "#f2d9d3",
        "eye_top": "#8447d0",
        "eye_mid": "#4b2f7f",
        "eye_bottom": "#24163d",
        "mouth": "#5b2a52",
        "tuft": "#ff9e88",
        "cheek": "#ffc1c2",
        "glow_idle": "#ff9c75",
        "glow_listening": "#ffb87f",
        "glow_thinking": "#caa1ff",
        "glow_speaking": "#ff7a90",
        "glow_error": "#ff5f76",
    },
    "mint": {
        "label": "Свежий",
        "motion_speed": 1.08,
        "motion_bob": 1.04,
        "glow_alpha": 1.02,
        "body_top": "#73f0d0",
        "body_mid": "#28a9a5",
        "body_bottom": "#103a52",
        "rim": "#c1fff0",
        "face_center": "#fbfffd",
        "face_edge": "#d9f3ea",
        "eye_top": "#2f7ca5",
        "eye_mid": "#16456f",
        "eye_bottom": "#0b2339",
        "mouth": "#1f5571",
        "tuft": "#48d2ba",
        "cheek": "#aff7ef",
        "glow_idle": "#64e9cf",
        "glow_listening": "#7af8e2",
        "glow_thinking": "#93dfff",
        "glow_speaking": "#5fc8ff",
        "glow_error": "#ff7d88",
    },
    "child": {
        "label": "Детский",
        "motion_speed": 1.18,
        "motion_bob": 1.22,
        "glow_alpha": 1.12,
        "body_top": "#8ec5ff",
        "body_mid": "#6d7cff",
        "body_bottom": "#362f7c",
        "rim": "#ffe28f",
        "face_center": "#fffdf8",
        "face_edge": "#f6e8ff",
        "eye_top": "#6a4fe3",
        "eye_mid": "#3b2c98",
        "eye_bottom": "#1f1951",
        "mouth": "#5a3fa5",
        "tuft": "#ffb86b",
        "cheek": "#ffc2d8",
        "glow_idle": "#8dbdff",
        "glow_listening": "#7de6ff",
        "glow_thinking": "#b1a7ff",
        "glow_speaking": "#ffb3d5",
        "glow_error": "#ff7f9c",
    },
    "minimal": {
        "label": "Минималистичный",
        "motion_speed": 0.82,
        "motion_bob": 0.7,
        "glow_alpha": 0.8,
        "body_top": "#dce7ff",
        "body_mid": "#95acd8",
        "body_bottom": "#3e5177",
        "rim": "#f7fbff",
        "face_center": "#ffffff",
        "face_edge": "#edf3ff",
        "eye_top": "#566783",
        "eye_mid": "#334056",
        "eye_bottom": "#182131",
        "mouth": "#4a5873",
        "tuft": "#8b9cbc",
        "cheek": "#dbe6ff",
        "glow_idle": "#b7c8ea",
        "glow_listening": "#d5e6ff",
        "glow_thinking": "#c7d2e8",
        "glow_speaking": "#a8c0e8",
        "glow_error": "#f0a5ae",
    },
}


def avatar_skin_spec(skin_id: str | None) -> dict:
    skins = avatar_skins()
    default_skin = skins[AVATAR_SKIN] if AVATAR_SKIN in skins else skins["classic"]
    return skins.get(skin_id or "", default_skin)


def avatar_skin_ids() -> list[str]:
    return list(avatar_skins().keys())


def avatar_skins() -> dict[str, dict]:
    skins = dict(AVATAR_SKINS)
    custom_skin = load_custom_skin_spec()
    if custom_skin is not None:
        skins["custom"] = custom_skin
    return skins


def custom_skin_path() -> Path:
    return Path(AVATAR_CUSTOM_SKIN_FILE)


def pack_manifest_path(pack_id: str) -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "assets"
        / "skins"
        / pack_id
        / "manifest.json"
    )


def available_pack_skin_ids() -> list[str]:
    result: list[str] = []
    for raw_id in AVATAR_PACK_SKINS:
        pack_id = str(raw_id or "").strip()
        if not pack_id:
            continue
        if pack_manifest_path(pack_id).exists():
            result.append(pack_id)
    return result


def pack_skin_combo_value(pack_id: str) -> str:
    return f"__pack_skin:{pack_id}"


def pack_skin_from_combo_value(value: str) -> str | None:
    prefix = "__pack_skin:"
    normalized = str(value or "").strip()
    if not normalized.startswith(prefix):
        return None
    pack_id = normalized[len(prefix):].strip()
    return pack_id or None


def normalize_custom_skin_spec(payload: dict) -> dict:
    base = dict(AVATAR_SKINS["classic"])
    label = (
        str(payload.get("label", "Пользовательский")).strip()
        or "Пользовательский"
    )
    base["label"] = label

    for key in (
        "body_top",
        "body_mid",
        "body_bottom",
        "rim",
        "face_center",
        "face_edge",
        "eye_top",
        "eye_mid",
        "eye_bottom",
        "mouth",
        "tuft",
        "cheek",
        "glow_idle",
        "glow_listening",
        "glow_thinking",
        "glow_speaking",
        "glow_error",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            base[key] = value.strip()

    for key in ("motion_speed", "motion_bob", "glow_alpha"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            base[key] = float(value)

    return base


def load_custom_skin_spec() -> dict | None:
    path = custom_skin_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return normalize_custom_skin_spec(payload)


def save_custom_skin_spec(payload: dict) -> None:
    path = custom_skin_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_custom_skin_spec(payload)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def delete_custom_skin_spec() -> None:
    path = custom_skin_path()
    if path.exists():
        path.unlink()


def exportable_skin_spec(skin_id: str | None) -> dict:
    skin = dict(avatar_skin_spec(skin_id))
    skin.setdefault("label", "Пользовательский")
    return skin
