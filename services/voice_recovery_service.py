from __future__ import annotations

import json
from pathlib import Path

from config.settings import (
    AUDIO_FILENAME,
    AVATAR_STATE_FILE,
    MIN_AUDIO_RMS,
    VOICE_AUTO_INTERRUPT_ADAPTIVE_ENABLED,
    VOICE_AUTO_INTERRUPT_HITS_NOISY,
    VOICE_AUTO_INTERRUPT_HITS_NORMAL,
    VOICE_AUTO_INTERRUPT_HITS_QUIET,
    VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD,
    VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD,
    VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS,
    VOICE_AUTO_INTERRUPT_TTS_ENABLED,
    VOICE_SMART_FOLLOWUP_ENABLED,
    VOICE_SMART_FOLLOWUP_LISTEN_SECONDS,
    VOICE_SMART_FOLLOWUP_RETRIES,
)
from services.speed_report_service import build_voice_auto_tune_plan
from voice.recorder import record_audio


def run_voice_mic_test(*, duration_seconds: float = 2.0) -> str:
    try:
        recording = record_audio(AUDIO_FILENAME, duration_seconds)
    except Exception:
        return "Не удалось проверить микрофон. Проверь доступ к микрофону в системе."

    if recording.rms < MIN_AUDIO_RMS:
        return "Слышу очень тихо. Попробуй говорить громче или поднести микрофон ближе."
    return "Микрофон работает. Слышу тебя нормально."


def apply_voice_auto_tune_from_metrics(*, limit: int = 40) -> str:
    state_path = Path(AVATAR_STATE_FILE)
    state = _load_state(state_path)
    current = _extract_current_voice_settings(state)

    plan = build_voice_auto_tune_plan(current=current, limit=limit)
    settings = plan.get("settings")
    if not isinstance(settings, dict) or not settings:
        return str(plan.get("summary", "Недостаточно данных для авто-тюнинга."))

    summary = str(plan.get("summary", "Авто-тюнинг выполнен."))
    if not bool(plan.get("applied", False)):
        return summary

    state.update(settings)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return f"{summary} Не удалось сохранить настройки в файл состояния."

    changed = plan.get("changed")
    if isinstance(changed, dict) and changed:
        labels = {
            "smart_followup_enabled": "умный follow-up",
            "smart_followup_listen_seconds": "окно дослушивания",
            "smart_followup_retries": "повторы follow-up",
            "auto_interrupt_tts_enabled": "прерывание озвучивания",
            "auto_interrupt_sample_seconds": "окно barge-in",
            "auto_interrupt_adaptive_enabled": "адаптивный auto-interrupt",
            "auto_interrupt_quiet_rms_threshold": "порог тихой среды",
            "auto_interrupt_noisy_rms_threshold": "порог шумной среды",
            "auto_interrupt_hits_quiet": "подтверждений (тихо)",
            "auto_interrupt_hits_normal": "подтверждений (обычно)",
            "auto_interrupt_hits_noisy": "подтверждений (шумно)",
        }
        changed_labels = [labels.get(str(key), str(key)) for key in changed.keys()]
        changed_text = ", ".join(changed_labels[:6])
        return f"{summary} Обновлено: {changed_text}."
    return summary


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _extract_current_voice_settings(state: dict) -> dict[str, float | int | bool]:
    return {
        "smart_followup_enabled": bool(state.get("smart_followup_enabled", VOICE_SMART_FOLLOWUP_ENABLED)),
        "smart_followup_listen_seconds": float(
            state.get("smart_followup_listen_seconds", VOICE_SMART_FOLLOWUP_LISTEN_SECONDS)
        ),
        "smart_followup_retries": int(state.get("smart_followup_retries", VOICE_SMART_FOLLOWUP_RETRIES)),
        "auto_interrupt_tts_enabled": bool(
            state.get("auto_interrupt_tts_enabled", VOICE_AUTO_INTERRUPT_TTS_ENABLED)
        ),
        "auto_interrupt_sample_seconds": float(
            state.get("auto_interrupt_sample_seconds", VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS)
        ),
        "auto_interrupt_adaptive_enabled": bool(
            state.get("auto_interrupt_adaptive_enabled", VOICE_AUTO_INTERRUPT_ADAPTIVE_ENABLED)
        ),
        "auto_interrupt_quiet_rms_threshold": float(
            state.get("auto_interrupt_quiet_rms_threshold", VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD)
        ),
        "auto_interrupt_noisy_rms_threshold": float(
            state.get("auto_interrupt_noisy_rms_threshold", VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD)
        ),
        "auto_interrupt_hits_quiet": int(state.get("auto_interrupt_hits_quiet", VOICE_AUTO_INTERRUPT_HITS_QUIET)),
        "auto_interrupt_hits_normal": int(state.get("auto_interrupt_hits_normal", VOICE_AUTO_INTERRUPT_HITS_NORMAL)),
        "auto_interrupt_hits_noisy": int(state.get("auto_interrupt_hits_noisy", VOICE_AUTO_INTERRUPT_HITS_NOISY)),
    }
