from __future__ import annotations

import json
import re
import time

from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable

from assistant.confirmations import confirmation_store
from assistant.child_mode import child_mode_store
from assistant.control import AssistantControlAction, assistant_control
from assistant.conversation import conversation_memory
from assistant.games import game_store
from assistant.state import AssistantStateName, assistant_state
from assistant.tone import conversation_tone
from config.settings import (
    AGENT_ROUTING_PROFILE,
    AUDIO_FILENAME,
    AVATAR_STATE_FILE,
    CHAT_FOLLOWUP_MAX_TURNS,
    MAX_VOICE_RETRIES,
    MIN_AUDIO_RMS,
    RECORD_SECONDS,
    STT_CONFIRMATION_LOGPROB_THRESHOLD,
    STT_CONFIRMATION_NO_SPEECH_THRESHOLD,
    VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS,
    VOICE_AUTO_INTERRUPT_TTS_ENABLED,
    VOICE_AUTO_INTERRUPT_ADAPTIVE_ENABLED,
    VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD,
    VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD,
    VOICE_AUTO_INTERRUPT_HITS_QUIET,
    VOICE_AUTO_INTERRUPT_HITS_NORMAL,
    VOICE_AUTO_INTERRUPT_HITS_NOISY,
    VOICE_EARLY_FAST_IMMEDIATE_INTENTS,
    VOICE_SMART_FOLLOWUP_ENABLED,
    VOICE_SMART_FOLLOWUP_LISTEN_SECONDS,
    VOICE_SMART_FOLLOWUP_RETRIES,
    VOICE_ULTRA_FAST_MAX_RECORD_SECONDS,
    VOICE_ULTRA_FAST_MODE,
    VOICE_ULTRA_FAST_SKIP_CONFIRM_FOR_FAST_INTENTS,
    CHAT_PROMPT_PACK_PROFILE,
)
from core.agent_policy import role_for_intent
from core.models import IntentResult
from core.orchestrator import process_text_detailed
from core.router import route_intent
from services.chat_service import generate_chat_reply_local_fast, get_last_chat_prompt_pack
from services.game_service import is_active_game_fast_phrase
from services.morning_show_service import get_morning_show_message
from services.runtime_prewarm_service import start_runtime_prewarm_async
from utils.chat_fast_replies import generate_local_chat_reply
from utils.intent_fastpaths import detect_early_fast_intent, detect_fast_intent
from utils.logger import log_interaction_event, log_voice_event
from utils.system_intents import detect_system_intent
from voice.recorder import record_audio
from voice.models import TranscriptionResult
from voice.stt import transcribe
from voice.tts import is_speaking, speak, stop_speaking

_PARTIAL_FAST_CHAT_PHRASES: dict[str, str] = {
    "да": "Понял, можно отвечать.",
    "угу": "Понял, можно отвечать.",
    "ага": "Понял, можно отвечать.",
    "нет": "Понял, можно отвечать.",
    "неа": "Понял, можно отвечать.",
    "стоп": "Понял, этого уже достаточно.",
    "замолчи": "Понял, этого уже достаточно.",
}

_PARTIAL_FAST_GAME_PHRASES: dict[str, str] = {
    "еще": "Понял игру, можно отвечать.",
    "ещё": "Понял игру, можно отвечать.",
    "еще раз": "Понял игру, можно отвечать.",
    "ещё раз": "Понял игру, можно отвечать.",
    "дальше": "Понял игру, можно отвечать.",
    "продолжай": "Понял игру, можно отвечать.",
    "подсказка": "Понял игру, можно отвечать.",
    "подскажи": "Понял игру, можно отвечать.",
    "повтори": "Понял игру, можно отвечать.",
    "давай другую": "Понял игру, можно отвечать.",
}

_EARLY_IMMEDIATE_INTENTS = {
    "stop_speaking",
    "exit_assistant",
    "open_text_command",
    "mic_test",
    "auto_tune_voice",
    "enable_child_mode",
    "disable_child_mode",
    "speed_report",
    "morning_show",
    "get_tasks",
    "get_events",
    "delete_tasks",
    "get_notes",
    "get_user_profile",
    "read_notion_page",
    "play_game",
    "sync_github_obsidian_project",
}

_BARGE_IN_SHORT_STOP = {"стоп", "замолчи", "хватит", "стоп вась", "вася стоп"}
_NOT_HEARD_REASONS = {
    "low_audio_level",
    "empty_transcription",
    "confirmation_failed",
    "retries_exhausted",
}
_CONSECUTIVE_NOT_HEARD_FAILURES = 0


@dataclass(frozen=True)
class CaptureOutcome:
    text: str | None
    failure_reason: str | None = None
    capture_ms: float = 0.0
    stt_ms: float = 0.0
    attempts: int = 0


@dataclass(frozen=True)
class BargeInOutcome:
    interrupted_text: str | None
    tts_ms: float
    likely_false: bool = False
    noise_mode: str = "normal"
    detect_rms: float | None = None
    detect_hits: int = 0


def run_voice_interaction() -> AssistantControlAction:
    start_runtime_prewarm_async()
    interaction_started = time.perf_counter()
    metrics = {
        "capture_ms": 0.0,
        "stt_ms": 0.0,
        "intent_ms": 0.0,
        "tts_ms": 0.0,
    }
    followup_turns_left = CHAT_FOLLOWUP_MAX_TURNS
    keep_conversation_open = False
    followup_config = _load_runtime_followup_config()
    auto_interrupt_config = _load_runtime_auto_interrupt_config()
    ab_profile_config = _load_runtime_ab_profiles()
    first_action_ms: float | None = None
    first_response_ms: float | None = None
    barge_in_count = 0
    barge_in_false_count = 0
    primary_intent: str | None = None
    primary_role: str | None = None
    role_counts: dict[str, int] = {}
    chat_pack_counts: dict[str, int] = {}
    local_fast_lane_hits = 0
    morning_show_message = get_morning_show_message()
    pending_user_text: str | None = None
    if morning_show_message:
        assistant_state.set(AssistantStateName.SPEAKING, morning_show_message)
        if first_response_ms is None:
            first_response_ms = (time.perf_counter() - interaction_started) * 1000
        barge_in_outcome = _speak_with_barge_in(
            morning_show_message,
            auto_interrupt_config,
        )
        metrics["tts_ms"] += barge_in_outcome.tts_ms
        if barge_in_outcome.interrupted_text:
            pending_user_text = barge_in_outcome.interrupted_text
            barge_in_count += 1
            if barge_in_outcome.likely_false:
                barge_in_false_count += 1
        time.sleep(0.25)

    while True:
        if pending_user_text:
            user_text = pending_user_text
            pending_user_text = None
            capture = CaptureOutcome(text=user_text)
        else:
            if keep_conversation_open and followup_config["enabled"]:
                assistant_state.set(AssistantStateName.LISTENING, "Если хочешь, ответь коротко…")
                capture = _capture_user_text(
                    record_seconds=float(followup_config["listen_seconds"]),
                    max_retries=int(followup_config["retries"]),
                    allow_voice_feedback=False,
                )
            else:
                assistant_state.set(AssistantStateName.LISTENING, "Говори, я слушаю...")
                capture = _capture_user_text()
        metrics["capture_ms"] += capture.capture_ms
        metrics["stt_ms"] += capture.stt_ms
        user_text = capture.text
        if not user_text:
            if keep_conversation_open:
                assistant_state.set(AssistantStateName.IDLE)
                _log_voice_perf(
                    metrics=metrics,
                    total_ms=(time.perf_counter() - interaction_started) * 1000,
                    status="followup_timeout",
                    failure_reason=capture.failure_reason,
                    first_action_ms=first_action_ms,
                    first_response_ms=first_response_ms,
                    barge_in_count=barge_in_count,
                    barge_in_false_count=barge_in_false_count,
                    not_heard_failure=_is_not_heard_failure(capture.failure_reason),
                    auto_interrupt_profile=_auto_interrupt_profile_name(auto_interrupt_config),
                    routing_profile=str(ab_profile_config.get("routing_profile", AGENT_ROUTING_PROFILE)),
                    prompt_pack_profile=str(ab_profile_config.get("prompt_pack_profile", CHAT_PROMPT_PACK_PROFILE)),
                    primary_intent=primary_intent,
                    primary_role=primary_role,
                    role_counts=role_counts,
                    chat_pack_counts=chat_pack_counts,
                    local_fast_lane_hits=local_fast_lane_hits,
                )
                return assistant_control.consume_action()
            streak = _register_capture_failure(capture.failure_reason)
            assistant_state.set(AssistantStateName.ERROR, "Не удалось распознать голосовую команду")
            tts_started = time.perf_counter()
            speak(_failure_message_for(capture.failure_reason, streak=streak))
            metrics["tts_ms"] += (time.perf_counter() - tts_started) * 1000
            assistant_state.set(AssistantStateName.IDLE)
            _log_voice_perf(
                metrics=metrics,
                total_ms=(time.perf_counter() - interaction_started) * 1000,
                status="capture_failed",
                failure_reason=capture.failure_reason,
                first_action_ms=first_action_ms,
                first_response_ms=first_response_ms,
                barge_in_count=barge_in_count,
                barge_in_false_count=barge_in_false_count,
                not_heard_failure=_is_not_heard_failure(capture.failure_reason),
                auto_interrupt_profile=_auto_interrupt_profile_name(auto_interrupt_config),
                routing_profile=str(ab_profile_config.get("routing_profile", AGENT_ROUTING_PROFILE)),
                prompt_pack_profile=str(ab_profile_config.get("prompt_pack_profile", CHAT_PROMPT_PACK_PROFILE)),
                primary_intent=primary_intent,
                primary_role=primary_role,
                role_counts=role_counts,
                chat_pack_counts=chat_pack_counts,
                local_fast_lane_hits=local_fast_lane_hits,
            )
            return assistant_control.consume_action()
        _reset_capture_failure_streak()

        print(f"Ты сказал: {user_text}")
        assistant_state.set(AssistantStateName.THINKING, _thinking_message_for(user_text))
        intent_started = time.perf_counter()
        result = _try_local_fast_lane(user_text)
        if result is None:
            result = process_text_detailed(user_text)
        else:
            local_fast_lane_hits += 1
        metrics["intent_ms"] += (time.perf_counter() - intent_started) * 1000
        current_intent = str(getattr(result, "intent", "unknown") or "unknown")
        current_role = str(getattr(result, "role", "chat_agent") or "chat_agent")
        if primary_intent is None:
            primary_intent = current_intent
        if primary_role is None:
            primary_role = current_role
        role_counts[current_role] = role_counts.get(current_role, 0) + 1
        if current_intent == "chat":
            chat_pack = get_last_chat_prompt_pack()
            if chat_pack:
                chat_pack_counts[chat_pack] = chat_pack_counts.get(chat_pack, 0) + 1
        if first_action_ms is None:
            first_action_ms = (time.perf_counter() - interaction_started) * 1000
        response = result.response
        if response:
            spoken_chunks: list[str] = []

            def _on_chunk_spoken(chunk: str) -> None:
                spoken_chunks.append(chunk)
                assistant_state.set(
                    AssistantStateName.SPEAKING,
                    " ".join(spoken_chunks).strip(),
                )

            if first_response_ms is None:
                first_response_ms = (time.perf_counter() - interaction_started) * 1000
            barge_in_outcome = _speak_with_barge_in(
                response,
                auto_interrupt_config,
                on_chunk=_on_chunk_spoken,
            )
            metrics["tts_ms"] += barge_in_outcome.tts_ms
            if barge_in_outcome.interrupted_text:
                pending_user_text = barge_in_outcome.interrupted_text
                keep_conversation_open = True
                barge_in_count += 1
                if barge_in_outcome.likely_false:
                    barge_in_false_count += 1
                continue

        if not result.needs_followup or followup_turns_left <= 0:
            break

        keep_conversation_open = True
        followup_turns_left -= 1
        time.sleep(0.18)

    assistant_state.set(AssistantStateName.IDLE)
    _log_voice_perf(
        metrics=metrics,
        total_ms=(time.perf_counter() - interaction_started) * 1000,
        status="ok",
        failure_reason=None,
        first_action_ms=first_action_ms,
        first_response_ms=first_response_ms,
        barge_in_count=barge_in_count,
        barge_in_false_count=barge_in_false_count,
        not_heard_failure=False,
        auto_interrupt_profile=_auto_interrupt_profile_name(auto_interrupt_config),
        routing_profile=str(ab_profile_config.get("routing_profile", AGENT_ROUTING_PROFILE)),
        prompt_pack_profile=str(ab_profile_config.get("prompt_pack_profile", CHAT_PROMPT_PACK_PROFILE)),
        primary_intent=primary_intent,
        primary_role=primary_role,
        role_counts=role_counts,
        chat_pack_counts=chat_pack_counts,
        local_fast_lane_hits=local_fast_lane_hits,
    )
    return assistant_control.consume_action()


def _load_runtime_followup_config() -> dict[str, float | int | bool]:
    defaults: dict[str, float | int | bool] = {
        "enabled": VOICE_SMART_FOLLOWUP_ENABLED,
        "listen_seconds": min(8.0, max(1.0, VOICE_SMART_FOLLOWUP_LISTEN_SECONDS)),
        "retries": min(3, max(1, VOICE_SMART_FOLLOWUP_RETRIES)),
    }

    path = Path(AVATAR_STATE_FILE)
    if not path.exists():
        return defaults

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(payload, dict):
        return defaults

    enabled = bool(payload.get("smart_followup_enabled", defaults["enabled"]))
    raw_seconds = payload.get("smart_followup_listen_seconds", defaults["listen_seconds"])
    raw_retries = payload.get("smart_followup_retries", defaults["retries"])

    try:
        listen_seconds = float(raw_seconds)
    except (TypeError, ValueError):
        listen_seconds = float(defaults["listen_seconds"])
    listen_seconds = min(8.0, max(1.0, listen_seconds))

    try:
        retries = int(raw_retries)
    except (TypeError, ValueError):
        retries = int(defaults["retries"])
    retries = min(3, max(1, retries))

    return {
        "enabled": enabled,
        "listen_seconds": listen_seconds,
        "retries": retries,
    }


def _load_runtime_auto_interrupt_config() -> dict[str, float | bool]:
    defaults: dict[str, float | bool] = {
        "enabled": VOICE_AUTO_INTERRUPT_TTS_ENABLED,
        "sample_seconds": min(3.0, max(0.5, VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS)),
        "adaptive_enabled": VOICE_AUTO_INTERRUPT_ADAPTIVE_ENABLED,
        "quiet_rms_threshold": max(50.0, VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD),
        "noisy_rms_threshold": max(
            max(50.0, VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD) + 20.0,
            VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD,
        ),
        "hits_quiet": max(1, VOICE_AUTO_INTERRUPT_HITS_QUIET),
        "hits_normal": max(1, VOICE_AUTO_INTERRUPT_HITS_NORMAL),
        "hits_noisy": max(1, VOICE_AUTO_INTERRUPT_HITS_NOISY),
    }

    path = Path(AVATAR_STATE_FILE)
    if not path.exists():
        return defaults

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(payload, dict):
        return defaults

    enabled = bool(payload.get("auto_interrupt_tts_enabled", defaults["enabled"]))
    raw_sample_seconds = payload.get("auto_interrupt_sample_seconds", defaults["sample_seconds"])
    adaptive_enabled = bool(payload.get("auto_interrupt_adaptive_enabled", defaults["adaptive_enabled"]))
    raw_quiet_rms = payload.get("auto_interrupt_quiet_rms_threshold", defaults["quiet_rms_threshold"])
    raw_noisy_rms = payload.get("auto_interrupt_noisy_rms_threshold", defaults["noisy_rms_threshold"])
    raw_hits_quiet = payload.get("auto_interrupt_hits_quiet", defaults["hits_quiet"])
    raw_hits_normal = payload.get("auto_interrupt_hits_normal", defaults["hits_normal"])
    raw_hits_noisy = payload.get("auto_interrupt_hits_noisy", defaults["hits_noisy"])
    try:
        sample_seconds = float(raw_sample_seconds)
    except (TypeError, ValueError):
        sample_seconds = float(defaults["sample_seconds"])
    sample_seconds = min(3.0, max(0.5, sample_seconds))
    try:
        quiet_rms_threshold = float(raw_quiet_rms)
    except (TypeError, ValueError):
        quiet_rms_threshold = float(defaults["quiet_rms_threshold"])
    quiet_rms_threshold = max(50.0, quiet_rms_threshold)
    try:
        noisy_rms_threshold = float(raw_noisy_rms)
    except (TypeError, ValueError):
        noisy_rms_threshold = float(defaults["noisy_rms_threshold"])
    noisy_rms_threshold = max(quiet_rms_threshold + 20.0, noisy_rms_threshold)
    try:
        hits_quiet = int(raw_hits_quiet)
    except (TypeError, ValueError):
        hits_quiet = int(defaults["hits_quiet"])
    try:
        hits_normal = int(raw_hits_normal)
    except (TypeError, ValueError):
        hits_normal = int(defaults["hits_normal"])
    try:
        hits_noisy = int(raw_hits_noisy)
    except (TypeError, ValueError):
        hits_noisy = int(defaults["hits_noisy"])
    hits_quiet = min(6, max(1, hits_quiet))
    hits_normal = min(6, max(1, hits_normal))
    hits_noisy = min(6, max(1, hits_noisy))

    return {
        "enabled": enabled,
        "sample_seconds": sample_seconds,
        "adaptive_enabled": adaptive_enabled,
        "quiet_rms_threshold": quiet_rms_threshold,
        "noisy_rms_threshold": noisy_rms_threshold,
        "hits_quiet": hits_quiet,
        "hits_normal": hits_normal,
        "hits_noisy": hits_noisy,
    }


def _load_runtime_ab_profiles() -> dict[str, str]:
    defaults = {
        "routing_profile": AGENT_ROUTING_PROFILE,
        "prompt_pack_profile": CHAT_PROMPT_PACK_PROFILE,
    }

    path = Path(AVATAR_STATE_FILE)
    if not path.exists():
        return defaults

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(payload, dict):
        return defaults

    routing_profile = str(payload.get("agent_routing_profile", AGENT_ROUTING_PROFILE)).strip()
    prompt_pack_profile = str(payload.get("chat_prompt_pack_profile", CHAT_PROMPT_PACK_PROFILE)).strip()
    return {
        "routing_profile": routing_profile or AGENT_ROUTING_PROFILE,
        "prompt_pack_profile": prompt_pack_profile or CHAT_PROMPT_PACK_PROFILE,
    }


def _speak_with_barge_in(
    text: str,
    auto_interrupt_config: dict[str, float | bool],
    on_chunk: Callable[[str], None] | None = None,
) -> BargeInOutcome:
    chunks = _split_tts_chunks(text)
    if not chunks:
        return BargeInOutcome(interrupted_text=None, tts_ms=0.0)

    if not bool(auto_interrupt_config.get("enabled", VOICE_AUTO_INTERRUPT_TTS_ENABLED)):
        started = time.perf_counter()
        for chunk in chunks:
            if on_chunk is not None:
                on_chunk(chunk)
            speak(chunk)
        return BargeInOutcome(
            interrupted_text=None,
            tts_ms=(time.perf_counter() - started) * 1000,
        )

    stop_event = Event()
    detected_lock = Lock()
    adaptive_enabled = bool(auto_interrupt_config.get("adaptive_enabled", True))
    quiet_rms_threshold = float(
        auto_interrupt_config.get("quiet_rms_threshold", VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD)
    )
    noisy_rms_threshold = float(
        auto_interrupt_config.get("noisy_rms_threshold", VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD)
    )
    if noisy_rms_threshold <= quiet_rms_threshold:
        noisy_rms_threshold = quiet_rms_threshold + 20.0
    hits_quiet = int(max(1, auto_interrupt_config.get("hits_quiet", VOICE_AUTO_INTERRUPT_HITS_QUIET)))
    hits_normal = int(max(1, auto_interrupt_config.get("hits_normal", VOICE_AUTO_INTERRUPT_HITS_NORMAL)))
    hits_noisy = int(max(1, auto_interrupt_config.get("hits_noisy", VOICE_AUTO_INTERRUPT_HITS_NOISY)))

    detected: dict[str, str | int | float | None] = {
        "text": None,
        "noise_mode": "normal",
        "detect_rms": None,
        "detect_hits": 0,
        "required_hits": 1,
    }
    candidate: dict[str, str | int] = {"text": "", "hits": 0}
    noise_ema_rms = max(0.0, quiet_rms_threshold * 0.8)

    sample_seconds = float(
        auto_interrupt_config.get("sample_seconds", VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS)
    )
    sample_duration = max(1, int(round(max(0.5, sample_seconds))))

    def _early_stop(partial_text: str) -> bool:
        resolved = _resolve_barge_in_text(partial_text)
        if not resolved:
            return False

        noise_mode = _classify_noise_mode(
            noise_ema_rms,
            quiet_rms_threshold=quiet_rms_threshold,
            noisy_rms_threshold=noisy_rms_threshold,
            adaptive_enabled=adaptive_enabled,
        )
        required_hits = _required_barge_hits(
            noise_mode,
            hits_quiet=hits_quiet,
            hits_normal=hits_normal,
            hits_noisy=hits_noisy,
            adaptive_enabled=adaptive_enabled,
        )

        with detected_lock:
            if candidate["text"] == resolved:
                candidate["hits"] = int(candidate["hits"]) + 1
            else:
                candidate["text"] = resolved
                candidate["hits"] = 1

            hits = int(candidate["hits"])
            if hits < required_hits:
                return False

            if detected["text"] is None:
                detected["text"] = resolved
                detected["noise_mode"] = noise_mode
                detected["detect_hits"] = hits
                detected["required_hits"] = required_hits
        return True

    def monitor() -> None:
        nonlocal noise_ema_rms
        while not stop_event.is_set():
            if not is_speaking():
                time.sleep(0.04)
                continue
            try:
                recording = record_audio(
                    AUDIO_FILENAME,
                    sample_duration,
                    early_stop_callback=_early_stop,
                )
            except Exception:
                time.sleep(0.05)
                continue

            sample_rms = max(0.0, float(recording.rms))
            noise_ema_rms = (noise_ema_rms * 0.65) + (sample_rms * 0.35)
            with detected_lock:
                has_detected = detected["text"] is not None
                if has_detected and detected["detect_rms"] is None:
                    detected["detect_rms"] = sample_rms
            if has_detected:
                stop_speaking()
                assistant_state.set(AssistantStateName.LISTENING, "Понял, переключаюсь на новую команду…")
                return
            if not is_speaking():
                return

    monitor_thread = Thread(target=monitor, daemon=True)
    monitor_thread.start()
    started = time.perf_counter()
    for chunk in chunks:
        with detected_lock:
            if detected["text"] is not None:
                break
        if on_chunk is not None:
            on_chunk(chunk)
        speak(chunk)
        with detected_lock:
            if detected["text"] is not None:
                break
    elapsed_ms = (time.perf_counter() - started) * 1000
    stop_event.set()
    monitor_thread.join(timeout=0.25)
    with detected_lock:
        interrupted = detected["text"]
        noise_mode = str(detected["noise_mode"])
        detect_rms = float(detected["detect_rms"]) if detected["detect_rms"] is not None else None
        detect_hits = int(detected["detect_hits"])
        required_hits = int(detected["required_hits"])

    likely_false = _is_likely_false_barge_in(
        interrupted_text=interrupted if isinstance(interrupted, str) else None,
        noise_mode=noise_mode,
        detect_hits=detect_hits,
        required_hits=required_hits,
    )
    return BargeInOutcome(
        interrupted_text=interrupted if isinstance(interrupted, str) else None,
        tts_ms=elapsed_ms,
        likely_false=likely_false,
        noise_mode=noise_mode,
        detect_rms=detect_rms,
        detect_hits=detect_hits,
    )


def _split_tts_chunks(text: str) -> list[str]:
    normalized = " ".join(str(text).strip().split())
    if not normalized:
        return []
    chunks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
    return chunks or [normalized]


def _resolve_barge_in_text(partial_text: str) -> str | None:
    normalized = " ".join(partial_text.lower().strip().split())
    if not normalized:
        return None

    if normalized in _BARGE_IN_SHORT_STOP or normalized.startswith("стоп "):
        return normalized

    if game_store.get() is not None and is_active_game_fast_phrase(normalized):
        return normalized

    system_intent = detect_system_intent(normalized)
    if system_intent is not None:
        return normalized

    fast_intent = detect_early_fast_intent(normalized)
    if fast_intent is None:
        return None
    if fast_intent.intent == "chat":
        return None

    return normalized


def _classify_noise_mode(
    rms: float,
    *,
    quiet_rms_threshold: float,
    noisy_rms_threshold: float,
    adaptive_enabled: bool,
) -> str:
    if not adaptive_enabled:
        return "normal"
    if rms >= noisy_rms_threshold:
        return "noisy"
    if rms <= quiet_rms_threshold:
        return "quiet"
    return "normal"


def _required_barge_hits(
    noise_mode: str,
    *,
    hits_quiet: int,
    hits_normal: int,
    hits_noisy: int,
    adaptive_enabled: bool,
) -> int:
    if not adaptive_enabled:
        return max(1, hits_normal)
    if noise_mode == "quiet":
        return max(1, hits_quiet)
    if noise_mode == "noisy":
        return max(1, hits_noisy)
    return max(1, hits_normal)


def _is_likely_false_barge_in(
    *,
    interrupted_text: str | None,
    noise_mode: str,
    detect_hits: int,
    required_hits: int,
) -> bool:
    if not interrupted_text:
        return False
    normalized = " ".join(interrupted_text.lower().strip().split())
    if not normalized:
        return True
    if noise_mode != "noisy":
        return False
    if detect_hits > max(1, required_hits):
        return False
    if normalized in _BARGE_IN_SHORT_STOP or normalized.startswith("стоп "):
        return True
    return len(normalized) <= 5


@dataclass(frozen=True)
class _FastLaneProcessResult:
    intent: str
    role: str
    response: str
    needs_followup: bool = False


def _try_local_fast_lane(user_text: str) -> _FastLaneProcessResult | None:
    # Не ускоряем, если ждем подтверждение или уже в активной игровой сессии:
    # там важна последовательная логика оркестратора.
    if confirmation_store.get() is not None:
        return None
    if game_store.get() is not None:
        return None

    system_intent = detect_system_intent(user_text)
    intent_result = system_intent or detect_fast_intent(user_text)
    if intent_result is None:
        return None

    if intent_result.intent == "chat":
        local_chat_reply = generate_chat_reply_local_fast(user_text)
        if local_chat_reply is None:
            return None
        log_interaction_event(
            "routing_step",
            {
                "step": "voice_local_fast_lane_chat",
                "user_text": user_text,
                "resolved_intent": "chat",
            },
        )
        return _FastLaneProcessResult(
            intent="chat",
            role="chat_agent",
            response=local_chat_reply,
            needs_followup=True,
        )

    fast_lane_intents = {
        "stop_speaking",
        "exit_assistant",
        "open_text_command",
        "mic_test",
        "auto_tune_voice",
        "enable_child_mode",
        "disable_child_mode",
        "speed_report",
        "morning_show",
        "create_task",
        "get_tasks",
        "delete_tasks",
        "create_note",
        "get_notes",
        "export_notes",
        "remember_user_profile",
        "forget_user_profile",
        "get_user_profile",
        "sync_github_notion",
        "sync_github_obsidian_project",
        "read_notion_page",
        "append_notion_page",
        "append_obsidian_note",
        "replace_obsidian_note",
        "get_events",
        "create_event",
        "delete_event",
    }
    if intent_result.intent not in fast_lane_intents:
        return None

    response = route_intent(intent_result, user_text)
    log_interaction_event(
        "routing_step",
        {
            "step": "voice_local_fast_lane",
            "user_text": user_text,
            "resolved_intent": intent_result.intent,
        },
    )
    return _FastLaneProcessResult(
        intent=intent_result.intent,
        role=role_for_intent(intent_result.intent),
        response=response,
        needs_followup=False,
    )


def _capture_user_text(
    *,
    record_seconds: float | None = None,
    max_retries: int | None = None,
    allow_voice_feedback: bool = True,
) -> CaptureOutcome:
    total_capture_ms = 0.0
    total_stt_ms = 0.0
    base_record_seconds = (
        float(record_seconds)
        if record_seconds is not None
        else (
            min(float(RECORD_SECONDS), max(1.0, VOICE_ULTRA_FAST_MAX_RECORD_SECONDS))
            if VOICE_ULTRA_FAST_MODE
            else float(RECORD_SECONDS)
        )
    )
    retries = max(1, int(max_retries) if max_retries is not None else MAX_VOICE_RETRIES)

    for attempt in range(1, retries + 1):
        log_voice_event(f"capture_attempt={attempt}/{retries}")
        record_started = time.perf_counter()
        recording = record_audio(
            AUDIO_FILENAME,
            int(max(1, round(base_record_seconds))),
            status_callback=_update_listening_status,
            partial_text_callback=_update_partial_transcript,
            early_stop_callback=_build_early_stop_callback(),
        )
        total_capture_ms += (time.perf_counter() - record_started) * 1000
        log_voice_event(f"recording_rms={recording.rms:.2f}")

        if recording.rms < MIN_AUDIO_RMS:
            log_voice_event(
                f"low_audio_level rms={recording.rms:.2f} threshold={MIN_AUDIO_RMS:.2f}"
            )
            if attempt < retries:
                if allow_voice_feedback:
                    speak("Слишком тихо. Повтори, пожалуйста, чуть громче.")
                continue
            log_voice_event("capture_failed reason=low_audio_level")
            return CaptureOutcome(
                text=None,
                failure_reason="low_audio_level",
                capture_ms=total_capture_ms,
                stt_ms=total_stt_ms,
                attempts=attempt,
            )

        stt_started = time.perf_counter()
        transcription = transcribe(AUDIO_FILENAME)
        total_stt_ms += (time.perf_counter() - stt_started) * 1000
        if transcription.is_empty:
            log_voice_event(
                "empty_transcription "
                f"language={transcription.language} "
                f"avg_logprob={transcription.avg_logprob} "
                f"no_speech_prob={transcription.no_speech_prob}"
            )
            if attempt < retries:
                if allow_voice_feedback:
                    speak("Я ничего не расслышал. Повтори, пожалуйста.")
                continue
            log_voice_event("capture_failed reason=empty_transcription")
            return CaptureOutcome(
                text=None,
                failure_reason="empty_transcription",
                capture_ms=total_capture_ms,
                stt_ms=total_stt_ms,
                attempts=attempt,
            )

        if _needs_confirmation(transcription):
            log_voice_event(
                "low_confidence_transcription "
                f"language={transcription.language} "
                f"avg_logprob={transcription.avg_logprob} "
                f"no_speech_prob={transcription.no_speech_prob} "
                f"text={transcription.text!r}"
            )
            confirmed_text = _confirm_transcription(transcription.text)
            if confirmed_text is None:
                if attempt < retries:
                    continue
                return CaptureOutcome(
                    text=None,
                    failure_reason="confirmation_failed",
                    capture_ms=total_capture_ms,
                    stt_ms=total_stt_ms,
                    attempts=attempt,
                )
            log_voice_event(f"transcription_confirmed text={confirmed_text!r}")
            return CaptureOutcome(
                text=confirmed_text,
                capture_ms=total_capture_ms,
                stt_ms=total_stt_ms,
                attempts=attempt,
            )

        log_voice_event(
            "transcription_success "
            f"language={transcription.language} "
            f"avg_logprob={transcription.avg_logprob} "
            f"no_speech_prob={transcription.no_speech_prob} "
            f"text={transcription.text!r}"
        )
        return CaptureOutcome(
            text=transcription.text,
            capture_ms=total_capture_ms,
            stt_ms=total_stt_ms,
            attempts=attempt,
        )

    log_voice_event("capture_failed reason=retries_exhausted")
    return CaptureOutcome(
        text=None,
        failure_reason="retries_exhausted",
        capture_ms=total_capture_ms,
        stt_ms=total_stt_ms,
        attempts=retries,
    )


def _update_listening_status(message: str) -> None:
    assistant_state.set(AssistantStateName.LISTENING, message)


def _update_partial_transcript(text: str) -> None:
    assistant_state.set(AssistantStateName.LISTENING, f"Похоже, ты сказал: {text}...")


def _build_early_stop_callback():
    last_intent_key: str | None = None

    def should_stop(partial_text: str) -> bool:
        nonlocal last_intent_key

        normalized_partial = " ".join(partial_text.lower().strip().split())
        if not normalized_partial:
            last_intent_key = None
            return False

        game_active = game_store.get() is not None
        if game_active:
            fast_game_status = _PARTIAL_FAST_GAME_PHRASES.get(normalized_partial)
            if fast_game_status is not None:
                assistant_state.set(AssistantStateName.LISTENING, fast_game_status)
                return True

        fast_chat_status = _PARTIAL_FAST_CHAT_PHRASES.get(normalized_partial)
        if fast_chat_status is not None:
            assistant_state.set(AssistantStateName.LISTENING, fast_chat_status)
            return True

        if normalized_partial.startswith("стоп "):
            assistant_state.set(AssistantStateName.LISTENING, "Понял, этого уже достаточно.")
            return True

        if is_active_game_fast_phrase(partial_text):
            assistant_state.set(AssistantStateName.LISTENING, "Понял игру, можно отвечать.")
            return True

        intent = detect_early_fast_intent(partial_text)
        if intent is None:
            last_intent_key = None
            return False

        intent_key = _intent_key(intent)
        if intent.intent in {"stop_speaking", "exit_assistant"}:
            assistant_state.set(AssistantStateName.LISTENING, "Понял, этого уже достаточно.")
            return True
        if VOICE_EARLY_FAST_IMMEDIATE_INTENTS and intent.intent in _EARLY_IMMEDIATE_INTENTS:
            if intent.intent == "chat":
                assistant_state.set(AssistantStateName.LISTENING, "Понял, можно отвечать сразу.")
            else:
                assistant_state.set(AssistantStateName.LISTENING, "Понял запрос, можно отвечать.")
            return True

        if intent_key == last_intent_key:
            if intent.intent == "chat":
                assistant_state.set(AssistantStateName.LISTENING, "Понял, можно отвечать сразу.")
            else:
                assistant_state.set(AssistantStateName.LISTENING, "Понял запрос, можно отвечать.")
            return True

        last_intent_key = intent_key
        return False

    return should_stop


def _needs_confirmation(transcription: TranscriptionResult) -> bool:
    if VOICE_ULTRA_FAST_MODE and VOICE_ULTRA_FAST_SKIP_CONFIRM_FOR_FAST_INTENTS:
        fast_intent = detect_fast_intent(transcription.text.strip())
        if fast_intent is not None and fast_intent.intent in {
            "chat",
            "play_game",
            "get_tasks",
            "get_events",
            "delete_tasks",
            "get_notes",
            "export_notes",
            "sync_github_notion",
            "sync_github_obsidian_project",
            "read_notion_page",
            "append_notion_page",
            "append_obsidian_note",
            "replace_obsidian_note",
            "morning_show",
            "remember_user_profile",
            "forget_user_profile",
            "get_user_profile",
        }:
            return False
    if _is_safe_low_confidence_fast_path(transcription):
        return False
    if transcription.avg_logprob is not None and transcription.avg_logprob < STT_CONFIRMATION_LOGPROB_THRESHOLD:
        return True
    if (
        transcription.no_speech_prob is not None
        and transcription.no_speech_prob > STT_CONFIRMATION_NO_SPEECH_THRESHOLD
    ):
        return True
    return False


def _thinking_message_for(user_text: str) -> str:
    recent_history = conversation_memory.recent()
    last_assistant_reply = next(
        (message.content for message in reversed(recent_history) if message.role == "assistant"),
        None,
    )
    if generate_local_chat_reply(
        user_text,
        history_size=len(recent_history),
        tone="child" if child_mode_store.is_enabled() else conversation_tone.current(),
        child_mode=child_mode_store.is_enabled(),
        last_assistant_reply=last_assistant_reply,
    ) is not None:
        return "Сейчас отвечу..."
    fast_intent = detect_fast_intent(user_text)
    if fast_intent is not None and fast_intent.intent == "chat":
        return "Секунду, подбираю ответ..."
    return "Секунду, разбираюсь..."


def _intent_key(intent: IntentResult) -> str:
    data_items = tuple(sorted((key, str(value)) for key, value in intent.data.items()))
    return f"{intent.intent}:{data_items}"


def _confirm_transcription(candidate_text: str) -> str | None:
    assistant_state.set(AssistantStateName.THINKING, "Проверяю, правильно ли расслышал")
    speak(f"Я услышал так: {candidate_text}. Если верно, скажи да. Если нет, просто повтори.")
    assistant_state.set(AssistantStateName.LISTENING)
    confirmation_recording = record_audio(AUDIO_FILENAME, RECORD_SECONDS)
    log_voice_event(f"confirmation_recording_rms={confirmation_recording.rms:.2f}")

    if confirmation_recording.rms < MIN_AUDIO_RMS:
        log_voice_event("confirmation_failed reason=low_audio_level")
        return None

    confirmation = transcribe(AUDIO_FILENAME)
    if confirmation.is_empty:
        log_voice_event("confirmation_failed reason=empty_transcription")
        return None

    normalized = confirmation.text.strip().lower()
    if normalized in {
        "да",
        "ага",
        "угу",
        "верно",
        "правильно",
        "все верно",
        "именно",
        "подтверждаю",
    }:
        return candidate_text

    return confirmation.text


def _is_safe_low_confidence_fast_path(transcription: TranscriptionResult) -> bool:
    text = transcription.text.strip()
    if not text:
        return False

    if transcription.no_speech_prob is not None and transcription.no_speech_prob > 0.2:
        return False

    if transcription.avg_logprob is not None:
        if transcription.avg_logprob < STT_CONFIRMATION_LOGPROB_THRESHOLD - 0.25:
            return False

    fast_intent = detect_fast_intent(text)
    if fast_intent is None:
        return False

    return fast_intent.intent in {
        "chat",
        "play_game",
        "get_tasks",
        "get_events",
        "delete_tasks",
        "get_notes",
        "export_notes",
        "sync_github_notion",
        "sync_github_obsidian_project",
        "read_notion_page",
        "append_notion_page",
        "append_obsidian_note",
        "replace_obsidian_note",
        "morning_show",
    }


def _failure_message_for(reason: str | None, *, streak: int = 0) -> str:
    recovery_hint = (
        " Давай коротко, 2-4 слова. И можно запустить тест микрофона в меню Васи."
        if streak >= 2
        else ""
    )
    if reason == "low_audio_level":
        return f"Было слишком тихо. Скажи еще раз чуть громче.{recovery_hint}"
    if reason == "empty_transcription":
        return f"Я не расслышала фразу. Попробуй сказать еще раз.{recovery_hint}"
    if reason == "confirmation_failed":
        return f"Я так и не разобрала фразу уверенно. Давай еще раз.{recovery_hint}"
    return f"Я так и не смогла нормально расслышать команду.{recovery_hint}"


def _register_capture_failure(reason: str | None) -> int:
    global _CONSECUTIVE_NOT_HEARD_FAILURES
    if _is_not_heard_failure(reason):
        _CONSECUTIVE_NOT_HEARD_FAILURES += 1
    else:
        _CONSECUTIVE_NOT_HEARD_FAILURES = 0
    return _CONSECUTIVE_NOT_HEARD_FAILURES


def _reset_capture_failure_streak() -> None:
    global _CONSECUTIVE_NOT_HEARD_FAILURES
    _CONSECUTIVE_NOT_HEARD_FAILURES = 0


def _is_not_heard_failure(reason: str | None) -> bool:
    if reason is None:
        return False
    return reason in _NOT_HEARD_REASONS


def _auto_interrupt_profile_name(auto_interrupt_config: dict[str, float | bool]) -> str:
    if not bool(auto_interrupt_config.get("enabled", True)):
        return "disabled"
    if bool(auto_interrupt_config.get("adaptive_enabled", True)):
        return "adaptive_v1"
    return "fixed_v1"


def _log_voice_perf(
    *,
    metrics: dict[str, float],
    total_ms: float,
    status: str,
    failure_reason: str | None,
    first_action_ms: float | None = None,
    first_response_ms: float | None = None,
    barge_in_count: int = 0,
    barge_in_false_count: int = 0,
    not_heard_failure: bool = False,
    auto_interrupt_profile: str = "adaptive_v1",
    routing_profile: str = AGENT_ROUTING_PROFILE,
    prompt_pack_profile: str = CHAT_PROMPT_PACK_PROFILE,
    primary_intent: str | None = None,
    primary_role: str | None = None,
    role_counts: dict[str, int] | None = None,
    chat_pack_counts: dict[str, int] | None = None,
    local_fast_lane_hits: int = 0,
) -> None:
    payload = {
        "status": status,
        "failure_reason": failure_reason,
        "capture_ms": round(metrics.get("capture_ms", 0.0), 2),
        "stt_ms": round(metrics.get("stt_ms", 0.0), 2),
        "intent_ms": round(metrics.get("intent_ms", 0.0), 2),
        "tts_ms": round(metrics.get("tts_ms", 0.0), 2),
        "total_ms": round(total_ms, 2),
        "first_action_ms": round(first_action_ms, 2) if first_action_ms is not None else None,
        "first_response_ms": round(first_response_ms, 2) if first_response_ms is not None else None,
        "barge_in_count": int(max(0, barge_in_count)),
        "barge_in_false_count": int(max(0, barge_in_false_count)),
        "not_heard_failure": bool(not_heard_failure),
        "auto_interrupt_profile": auto_interrupt_profile,
        "routing_profile": routing_profile,
        "prompt_pack_profile": prompt_pack_profile,
        "primary_intent": primary_intent or "",
        "primary_role": primary_role or "",
        "role_counts": dict(role_counts or {}),
        "chat_pack_counts": dict(chat_pack_counts or {}),
        "local_fast_lane_hits": int(max(0, local_fast_lane_hits)),
    }
    log_interaction_event("voice_perf", payload)
