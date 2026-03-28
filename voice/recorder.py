from typing import Callable

from voice.backends import RecordingResult, get_voice_input_backend


def record_audio(
    filename: str,
    duration: int,
    samplerate: int = 44100,
    status_callback: Callable[[str], None] | None = None,
    partial_text_callback: Callable[[str], None] | None = None,
    early_stop_callback: Callable[[str], bool] | None = None,
) -> RecordingResult:
    backend = get_voice_input_backend()
    return backend.record(
        filename=filename,
        duration=duration,
        samplerate=samplerate,
        status_callback=status_callback,
        partial_text_callback=partial_text_callback,
        early_stop_callback=early_stop_callback,
    )
