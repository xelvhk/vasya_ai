from voice.backends import RecordingResult, get_voice_input_backend


def record_audio(filename: str, duration: int, samplerate: int = 44100) -> RecordingResult:
    backend = get_voice_input_backend()
    return backend.record(filename=filename, duration=duration, samplerate=samplerate)
