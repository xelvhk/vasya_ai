from __future__ import annotations

from faster_whisper import WhisperModel

from config.settings import STT_BEAM_SIZE, STT_LANGUAGE, STT_PARTIAL_MAX_WORDS, WHISPER_MODEL
from voice.models import TranscriptionResult

_model = WhisperModel(WHISPER_MODEL)


def transcribe(audio_path: str) -> TranscriptionResult:
    segments, info = _model.transcribe(
        audio_path,
        beam_size=STT_BEAM_SIZE,
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
    segments, _ = _model.transcribe(
        audio_path,
        beam_size=1,
        language=STT_LANGUAGE,
        vad_filter=True,
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()
    if not text:
        return ""
    words = text.split()
    return " ".join(words[:STT_PARTIAL_MAX_WORDS]).strip()
