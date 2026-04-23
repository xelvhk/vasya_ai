from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from assistant.child_mode import child_mode_store
from config.settings import PIPER_MODEL_PATH, TTS_PROFILE, TTS_STATE_FILE, XTTS_SPEAKER_WAV


@dataclass(frozen=True)
class VoiceProfile:
    profile_id: str
    label: str
    backend: str
    gender: str
    character: str
    piper_model_name: str | None = None
    piper_length_scale: float | None = None
    xtts_speaker_wav: str | None = None
    xtts_language: str | None = None
    say_voice: str | None = None
    say_rate: int | None = None


VOICE_PROFILES: tuple[VoiceProfile, ...] = (
    VoiceProfile(
        profile_id="ruslan_direct",
        label="Руслан — энергичный и прямой",
        backend="piper",
        gender="мужской",
        character="быстрый, четкий, напористый",
        piper_model_name="ru_RU-ruslan-medium.onnx",
        piper_length_scale=0.76,
        say_voice="Milena",
        say_rate=220,
    ),
    VoiceProfile(
        profile_id="ruslan_child",
        label="Руслан — мягкий детский режим",
        backend="piper",
        gender="мужской",
        character="мягкий, спокойный, дружелюбный",
        piper_model_name="ru_RU-ruslan-medium.onnx",
        piper_length_scale=0.88,
        say_voice="Milena",
        say_rate=205,
    ),
    VoiceProfile(
        profile_id="alexa_natural_xtts",
        label="Алекса — натуральный XTTS",
        backend="xtts",
        gender="женский",
        character="более живой, мягкий, разговорный",
        xtts_speaker_wav=XTTS_SPEAKER_WAV or None,
        xtts_language="ru",
        say_voice="Milena",
        say_rate=195,
    ),
)


_VOICE_PROFILE_MAP = {profile.profile_id: profile for profile in VOICE_PROFILES}


def list_voice_profiles() -> list[VoiceProfile]:
    return list(VOICE_PROFILES)


def get_voice_profile(profile_id: str | None = None) -> VoiceProfile:
    selected_id = profile_id or get_active_voice_profile_id()
    profile = _VOICE_PROFILE_MAP.get(selected_id)
    if profile is not None:
        return profile
    return _VOICE_PROFILE_MAP["ruslan_direct"]


def get_active_voice_profile_id() -> str:
    stored = _load_tts_state().get("profile_id")
    if isinstance(stored, str) and stored in _VOICE_PROFILE_MAP:
        return stored
    if TTS_PROFILE in _VOICE_PROFILE_MAP:
        return TTS_PROFILE
    return "ruslan_direct"


def get_active_voice_profile() -> VoiceProfile:
    profile = get_voice_profile(get_active_voice_profile_id())
    if child_mode_store.is_enabled() and profile.profile_id == "ruslan_direct":
        return get_voice_profile("ruslan_child")
    return profile


def set_active_voice_profile(profile_id: str) -> VoiceProfile:
    profile = get_voice_profile(profile_id)
    _save_tts_state({"profile_id": profile.profile_id})
    return profile


def get_profile_model_path(profile: VoiceProfile | None = None) -> Path | None:
    resolved_profile = profile or get_active_voice_profile()
    model_name = resolved_profile.piper_model_name
    if model_name:
        candidate = Path(PIPER_MODEL_PATH).resolve().parent / model_name
        if candidate.exists():
            return candidate

    configured_path = Path(PIPER_MODEL_PATH).expanduser()
    if configured_path.exists():
        return configured_path
    return None


def get_profile_speaker_wav(profile: VoiceProfile | None = None) -> Path | None:
    resolved_profile = profile or get_active_voice_profile()
    speaker = (resolved_profile.xtts_speaker_wav or "").strip()
    if not speaker:
        return None
    candidate = Path(speaker).expanduser()
    if candidate.exists():
        return candidate
    return None


def is_profile_installed(profile: VoiceProfile | None = None) -> bool:
    resolved_profile = profile or get_active_voice_profile()
    if resolved_profile.backend == "piper":
        return get_profile_model_path(resolved_profile) is not None
    if resolved_profile.backend == "xtts":
        return get_profile_speaker_wav(resolved_profile) is not None
    return True


def _load_tts_state() -> dict:
    state_path = Path(TTS_STATE_FILE)
    if not state_path.exists():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_tts_state(state: dict) -> None:
    state_path = Path(TTS_STATE_FILE)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
