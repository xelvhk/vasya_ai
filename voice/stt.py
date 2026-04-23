from __future__ import annotations

from faster_whisper import WhisperModel

from config.settings import (
    STT_QUALITY_PROFILE,
    STT_FINAL_BEAM_SIZE,
    STT_LANGUAGE,
    STT_PARTIAL_BEAM_SIZE,
    STT_PARTIAL_MAX_WORDS,
    WHISPER_FINAL_MODEL,
    WHISPER_PARTIAL_MODEL,
)
from utils.logger import log_voice_event
from voice.models import TranscriptionResult


_MODEL_CACHE: dict[str, WhisperModel] = {}
_FAILED_MODEL_NAMES: set[str] = set()
_MODEL_USAGE_LOGGED: set[tuple[str, str]] = set()


def transcribe(audio_path: str) -> TranscriptionResult:
    model = _get_model_with_fallback(
        preferred_model_name=WHISPER_FINAL_MODEL,
        fallback_model_name=WHISPER_PARTIAL_MODEL,
        purpose="final",
    )
    segments, info = model.transcribe(
        audio_path,
        beam_size=STT_FINAL_BEAM_SIZE,
        language=STT_LANGUAGE,
        vad_filter=True,
    )
    segment_list = list(segments)
    text = " ".join(segment.text.strip() for segment in segment_list).strip()

    avg_logprob = None
    no_speech_prob = None
    if segment_list:
        avg_logprob = sum(segment.avg_logprob for segment in segment_list) / len(segment_list)
        no_speech_prob = sum(segment.no_speech_prob for segment in segment_list) / len(segment_list)

    return TranscriptionResult(
        text=text,
        language=getattr(info, "language", None),
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
    )


def transcribe_partial(audio_path: str) -> str:
    model = _get_model_with_fallback(
        preferred_model_name=WHISPER_PARTIAL_MODEL,
        fallback_model_name=WHISPER_PARTIAL_MODEL,
        purpose="partial",
    )
    segments, _ = model.transcribe(
        audio_path,
        beam_size=STT_PARTIAL_BEAM_SIZE,
        language=STT_LANGUAGE,
        vad_filter=True,
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()
    if not text:
        return ""
    words = text.split()
    return " ".join(words[:STT_PARTIAL_MAX_WORDS]).strip()


def prewarm_stt_models(*, include_final: bool = True) -> None:
    try:
        _get_model_with_fallback(
            preferred_model_name=WHISPER_PARTIAL_MODEL,
            fallback_model_name=WHISPER_PARTIAL_MODEL,
            purpose="partial",
        )
        if include_final:
            _get_model_with_fallback(
                preferred_model_name=WHISPER_FINAL_MODEL,
                fallback_model_name=WHISPER_PARTIAL_MODEL,
                purpose="final",
            )
        log_voice_event(
            "stt_prewarm_done "
            f"partial={WHISPER_PARTIAL_MODEL!r} final={WHISPER_FINAL_MODEL!r} "
            f"include_final={str(include_final).lower()}"
        )
    except Exception as exc:
        log_voice_event(f"stt_prewarm_failed error={type(exc).__name__}: {exc}")


def _get_model(model_name: str) -> WhisperModel:
    model = _MODEL_CACHE.get(model_name)
    if model is not None:
        return model

    model = WhisperModel(model_name)
    _MODEL_CACHE[model_name] = model
    return model


def _get_model_with_fallback(
    *,
    preferred_model_name: str,
    fallback_model_name: str,
    purpose: str,
) -> WhisperModel:
    if preferred_model_name not in _FAILED_MODEL_NAMES:
        try:
            model = _get_model(preferred_model_name)
            _log_model_usage(
                purpose=purpose,
                model_name=preferred_model_name,
                beam_size=STT_FINAL_BEAM_SIZE if purpose == "final" else STT_PARTIAL_BEAM_SIZE,
            )
            return model
        except Exception as exc:
            _FAILED_MODEL_NAMES.add(preferred_model_name)
            if preferred_model_name != fallback_model_name:
                log_voice_event(
                    f"stt_model_fallback purpose={purpose} preferred={preferred_model_name!r} "
                    f"fallback={fallback_model_name!r} error={type(exc).__name__}: {exc}"
                )

    model = _get_model(fallback_model_name)
    _log_model_usage(
        purpose=purpose,
        model_name=fallback_model_name,
        beam_size=STT_FINAL_BEAM_SIZE if purpose == "final" else STT_PARTIAL_BEAM_SIZE,
        fallback_used=True,
    )
    return model


def _log_model_usage(
    *,
    purpose: str,
    model_name: str,
    beam_size: int,
    fallback_used: bool = False,
) -> None:
    key = (purpose, model_name)
    if key in _MODEL_USAGE_LOGGED:
        return
    _MODEL_USAGE_LOGGED.add(key)
    log_voice_event(
        "stt_model_active "
        f"profile={STT_QUALITY_PROFILE!r} "
        f"purpose={purpose} model={model_name!r} beam={beam_size} "
        f"fallback_used={str(fallback_used).lower()}"
    )
