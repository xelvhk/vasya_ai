from __future__ import annotations

import threading

from config.settings import (
    OLLAMA_FAST_MODEL,
    VOICE_RUNTIME_PREWARM_ENABLED,
    VOICE_RUNTIME_PREWARM_OLLAMA,
    VOICE_RUNTIME_PREWARM_OLLAMA_CHAT,
    VOICE_RUNTIME_PREWARM_OLLAMA_TIMEOUT_SECONDS,
    VOICE_RUNTIME_PREWARM_STT,
)
from services.ollama_client import (
    OllamaClientError,
    ensure_ollama_running,
    generate,
    resolve_chat_model,
)
from services.morning_show_service import prewarm_morning_show_async
from utils.logger import log_voice_event
from voice.stt import prewarm_stt_models

_PREWARM_LOCK = threading.Lock()
_PREWARM_STARTED = False


def start_runtime_prewarm_async() -> None:
    global _PREWARM_STARTED
    if not VOICE_RUNTIME_PREWARM_ENABLED:
        return
    with _PREWARM_LOCK:
        if _PREWARM_STARTED:
            return
        _PREWARM_STARTED = True
    thread = threading.Thread(target=_run_prewarm, daemon=True, name="voice-runtime-prewarm")
    thread.start()


def _run_prewarm() -> None:
    log_voice_event("runtime_prewarm_start")
    prewarm_morning_show_async()
    if VOICE_RUNTIME_PREWARM_STT:
        prewarm_stt_models(include_final=True)

    if VOICE_RUNTIME_PREWARM_OLLAMA:
        _prewarm_ollama()
    log_voice_event("runtime_prewarm_done")


def _prewarm_ollama() -> None:
    try:
        ensure_ollama_running(timeout_seconds=VOICE_RUNTIME_PREWARM_OLLAMA_TIMEOUT_SECONDS)
    except OllamaClientError as exc:
        log_voice_event(f"runtime_prewarm_ollama_unavailable error={exc}")
        return

    _prewarm_model(OLLAMA_FAST_MODEL, tag="fast")
    if VOICE_RUNTIME_PREWARM_OLLAMA_CHAT:
        chat_model = resolve_chat_model()
        if chat_model != OLLAMA_FAST_MODEL:
            _prewarm_model(chat_model, tag="chat")


def _prewarm_model(model_name: str, *, tag: str) -> None:
    try:
        generate(
            "ok",
            model=model_name,
            think=False,
            temperature=0.0,
            num_predict=4,
        )
        log_voice_event(f"runtime_prewarm_model_ok tag={tag} model={model_name!r}")
    except Exception as exc:
        log_voice_event(
            f"runtime_prewarm_model_failed tag={tag} model={model_name!r} "
            f"error={type(exc).__name__}: {exc}"
        )
