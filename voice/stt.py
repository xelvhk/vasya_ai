from __future__ import annotations

from faster_whisper import WhisperModel

from config.settings import (
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
            return _get_model(preferred_model_name)
        except Exception as exc:
            _FAILED_MODEL_NAMES.add(preferred_model_name)
            if preferred_model_name != fallback_model_name:
                log_voice_event(
                    f"stt_model_fallback purpose={purpose} preferred={preferred_model_name!r} "
                    f"fallback={fallback_model_name!r} error={type(exc).__name__}: {exc}"
                )

    return _get_model(fallback_model_name)
