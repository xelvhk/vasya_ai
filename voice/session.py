from __future__ import annotations

from assistant.state import AssistantStateName, assistant_state
from config.settings import AUDIO_FILENAME, MAX_VOICE_RETRIES, MIN_AUDIO_RMS, RECORD_SECONDS
from core.orchestrator import process_text
from services.ollama_client import OllamaClientError, ensure_ollama_running
from utils.logger import log_voice_event
from voice.recorder import record_audio
from voice.stt import transcribe
from voice.tts import speak


def run_voice_interaction() -> None:
    try:
        ensure_ollama_running()
    except OllamaClientError as exc:
        message = str(exc)
        assistant_state.set(AssistantStateName.ERROR, message)
        print(message)
        speak(message)
        assistant_state.set(AssistantStateName.IDLE)
        return

    assistant_state.set(AssistantStateName.LISTENING)
    user_text = _capture_user_text()
    if not user_text:
        assistant_state.set(AssistantStateName.ERROR, "Не удалось распознать голосовую команду")
        speak("Я так и не смог нормально расслышать команду.")
        assistant_state.set(AssistantStateName.IDLE)
        return

    print(f"Ты сказал: {user_text}")
    assistant_state.set(AssistantStateName.THINKING)
    response = process_text(user_text)
    assistant_state.set(AssistantStateName.SPEAKING, response)
    speak(response)
    assistant_state.set(AssistantStateName.IDLE)


def _capture_user_text() -> str | None:
    for attempt in range(1, MAX_VOICE_RETRIES + 1):
        log_voice_event(f"capture_attempt={attempt}/{MAX_VOICE_RETRIES}")
        recording = record_audio(AUDIO_FILENAME, RECORD_SECONDS)
        log_voice_event(f"recording_rms={recording.rms:.2f}")

        if recording.rms < MIN_AUDIO_RMS:
            log_voice_event(
                f"low_audio_level rms={recording.rms:.2f} threshold={MIN_AUDIO_RMS:.2f}"
            )
            if attempt < MAX_VOICE_RETRIES:
                speak("Слишком тихо. Повтори, пожалуйста, чуть громче.")
                continue
            log_voice_event("capture_failed reason=low_audio_level")
            return None

        transcription = transcribe(AUDIO_FILENAME)
        if transcription.is_empty:
            log_voice_event(
                "empty_transcription "
                f"language={transcription.language} "
                f"avg_logprob={transcription.avg_logprob} "
                f"no_speech_prob={transcription.no_speech_prob}"
            )
            if attempt < MAX_VOICE_RETRIES:
                speak("Я ничего не расслышал. Повтори, пожалуйста.")
                continue
            log_voice_event("capture_failed reason=empty_transcription")
            return None

        log_voice_event(
            "transcription_success "
            f"language={transcription.language} "
            f"avg_logprob={transcription.avg_logprob} "
            f"no_speech_prob={transcription.no_speech_prob} "
            f"text={transcription.text!r}"
        )
        return transcription.text

    log_voice_event("capture_failed reason=retries_exhausted")
    return None
