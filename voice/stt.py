from faster_whisper import WhisperModel
from config.settings import WHISPER_MODEL

_model = WhisperModel(WHISPER_MODEL)

def transcribe(audio_path: str) -> str:
    segments, _ = _model.transcribe(audio_path)
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return text