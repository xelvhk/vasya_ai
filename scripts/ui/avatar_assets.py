from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from assistant.state import AssistantStateName


AVATAR_PACK_STATE_KEYS = {"idle", "listening", "thinking", "speaking", "error"}
AVATAR_PACK_TIMING_DEFAULTS = {
    "idle": 260,
    "listening": 180,
    "thinking": 200,
    "speaking": 90,
    "error": 150,
}


@dataclass(frozen=True)
class AvatarPackLoadResult:
    frames: dict[str, list[Any]]
    timing_ms: dict[str, int]
    frame_index: dict[str, int]

    @property
    def loaded(self) -> bool:
        return bool(self.frames)


def resolve_avatar_path(widget_state: dict, configured_path: str | Path | None) -> Path | None:
    override_path = str(widget_state.get("avatar_image_path", "")).strip()
    if override_path:
        path = Path(override_path).expanduser()
        if path.exists():
            return path

    if not configured_path:
        return None
    path = Path(configured_path).expanduser()
    if not path.exists():
        return None
    return path


def avatar_state_key(state_name: AssistantStateName) -> str:
    if state_name == AssistantStateName.LISTENING:
        return "listening"
    if state_name == AssistantStateName.THINKING:
        return "thinking"
    if state_name == AssistantStateName.SPEAKING:
        return "speaking"
    if state_name == AssistantStateName.ERROR:
        return "error"
    return "idle"


def cached_avatar_pack_result(payload: dict | None) -> AvatarPackLoadResult | None:
    if not isinstance(payload, dict):
        return None
    raw_frames = payload.get("frames")
    raw_timing = payload.get("timing_ms")
    if not isinstance(raw_frames, dict) or not isinstance(raw_timing, dict):
        return None

    frames = {
        str(key): list(value)
        for key, value in raw_frames.items()
        if isinstance(value, list) and value
    }
    timing_ms = {
        str(key): int(value)
        for key, value in raw_timing.items()
    }
    frame_index = {key: 0 for key, value in frames.items() if value}
    if not frames:
        return None
    return AvatarPackLoadResult(frames=frames, timing_ms=timing_ms, frame_index=frame_index)


def avatar_pack_cache_payload(result: AvatarPackLoadResult) -> dict[str, dict]:
    return {
        "frames": {key: list(value) for key, value in result.frames.items()},
        "timing_ms": dict(result.timing_ms),
    }


def load_avatar_pack_manifest(
    manifest_path: Path,
    pixmap_factory: Callable[[str], Any],
) -> AvatarPackLoadResult:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AvatarPackLoadResult(frames={}, timing_ms={}, frame_index={})
    if not isinstance(payload, dict):
        return AvatarPackLoadResult(frames={}, timing_ms={}, frame_index={})

    raw_states = payload.get("states")
    if not isinstance(raw_states, dict):
        return AvatarPackLoadResult(frames={}, timing_ms={}, frame_index={})

    frames = _load_avatar_pack_frames(
        raw_states,
        base_dir=manifest_path.parent,
        pixmap_factory=pixmap_factory,
    )
    if not frames:
        return AvatarPackLoadResult(frames={}, timing_ms={}, frame_index={})

    return AvatarPackLoadResult(
        frames=frames,
        timing_ms=_avatar_pack_timing(payload.get("timing_ms")),
        frame_index={key: 0 for key in frames},
    )


def pack_frames_for_state(frames: dict[str, list[Any]], state_key: str) -> list[Any]:
    return frames.get(state_key) or frames.get("idle") or []


def _load_avatar_pack_frames(
    raw_states: dict,
    *,
    base_dir: Path,
    pixmap_factory: Callable[[str], Any],
) -> dict[str, list[Any]]:
    frames_by_state: dict[str, list[Any]] = {}
    for key, value in raw_states.items():
        state_key = str(key).strip().lower()
        if state_key not in AVATAR_PACK_STATE_KEYS:
            continue
        if not isinstance(value, list):
            continue
        frames = []
        for item in value:
            candidate = base_dir / str(item).strip()
            pixmap = pixmap_factory(str(candidate))
            if pixmap.isNull():
                continue
            frames.append(pixmap)
        if frames:
            frames_by_state[state_key] = frames
    return frames_by_state


def _avatar_pack_timing(raw_timing: Any) -> dict[str, int]:
    timing = {}
    if isinstance(raw_timing, dict):
        for key, default_value in AVATAR_PACK_TIMING_DEFAULTS.items():
            raw_value = raw_timing.get(key, default_value)
            try:
                timing[key] = min(2000, max(40, int(raw_value)))
            except (TypeError, ValueError):
                timing[key] = default_value
        return timing
    return dict(AVATAR_PACK_TIMING_DEFAULTS)
