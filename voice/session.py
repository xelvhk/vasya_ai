from __future__ import annotations

import time

from assistant.child_mode import child_mode_store
from assistant.control import AssistantControlAction, assistant_control
from assistant.conversation import conversation_memory
from assistant.state import AssistantStateName, assistant_state
from assistant.tone import conversation_tone
from config.settings import (
    AUDIO_FILENAME,
    CHAT_FOLLOWUP_MAX_TURNS,
    INTERRUPT_LISTEN_DELAY_SECONDS,
    MAX_VOICE_RETRIES,
    MIN_AUDIO_RMS,
    RECORD_SECONDS,
    STT_CONFIRMATION_LOGPROB_THRESHOLD,
    STT_CONFIRMATION_NO_SPEECH_THRESHOLD,
)
from core.models import IntentResult
from core.orchestrator import process_text_detailed
from services.ollama_client import OllamaClientError, ensure_ollama_running
from utils.chat_fast_replies import generate_local_chat_reply
from utils.logger import log_voice_event
from voice.recorder import record_audio
from voice.models import TranscriptionResult
from voice.stt import transcribe
from voice.tts import speak
from utils.intent_fastpaths import detect_early_fast_intent, detect_fast_intent


def run_voice_interaction() -> AssistantControlAction:
    try:
        ensure_ollama_running()
    except OllamaClientError as exc:
        message = str(exc)
        assistant_state.set(AssistantStateName.ERROR, message)
        print(message)
        speak(message)
        assistant_state.set(AssistantStateName.IDLE)
        return assistant_control.consume_action()

    followup_turns_left = CHAT_FOLLOWUP_MAX_TURNS
    keep_conversation_open = False

    while True:
        assistant_state.set(AssistantStateName.LISTENING, "Говори, я слушаю...")
        user_text = _capture_user_text()
        if not user_text:
            if keep_conversation_open:
                assistant_state.set(AssistantStateName.IDLE)
                return assistant_control.consume_action()
            assistant_state.set(AssistantStateName.ERROR, "Не удалось распознать голосовую команду")
            speak("Я так и не смог нормально расслышать команду.")
            assistant_state.set(AssistantStateName.IDLE)
            return assistant_control.consume_action()

        print(f"Ты сказал: {user_text}")
        assistant_state.set(AssistantStateName.THINKING, _thinking_message_for(user_text))
        result = process_text_detailed(user_text)
        response = result.response
        if response:
            assistant_state.set(AssistantStateName.SPEAKING, response)
            speak(response)

        if not _should_keep_conversation_open(result.intent, response) or followup_turns_left <= 0:
            break

        keep_conversation_open = True
        followup_turns_left -= 1
        time.sleep(INTERRUPT_LISTEN_DELAY_SECONDS)

    assistant_state.set(AssistantStateName.IDLE)
    return assistant_control.consume_action()


def _should_keep_conversation_open(intent: str, response: str) -> bool:
    if intent in {"chat", "unknown", "play_game"}:
        return True
    return response.strip().endswith("?")


def _capture_user_text() -> str | None:
    for attempt in range(1, MAX_VOICE_RETRIES + 1):
        log_voice_event(f"capture_attempt={attempt}/{MAX_VOICE_RETRIES}")
        recording = record_audio(
            AUDIO_FILENAME,
            RECORD_SECONDS,
            status_callback=_update_listening_status,
            partial_text_callback=_update_partial_transcript,
            early_stop_callback=_build_early_stop_callback(),
        )
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
                if attempt < MAX_VOICE_RETRIES:
                    continue
                return None
            log_voice_event(f"transcription_confirmed text={confirmed_text!r}")
            return confirmed_text

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


def _update_listening_status(message: str) -> None:
    assistant_state.set(AssistantStateName.LISTENING, message)


def _update_partial_transcript(text: str) -> None:
    assistant_state.set(AssistantStateName.LISTENING, f"Похоже, ты сказал: {text}...")


def _build_early_stop_callback():
    last_intent_key: str | None = None

    def should_stop(partial_text: str) -> bool:
        nonlocal last_intent_key

        intent = detect_early_fast_intent(partial_text)
        if intent is None:
            last_intent_key = None
            return False

        intent_key = _intent_key(intent)
        if intent.intent in {"stop_speaking", "exit_assistant"}:
            assistant_state.set(AssistantStateName.LISTENING, "Понял, этого уже достаточно.")
            return True

        if intent_key == last_intent_key:
            assistant_state.set(AssistantStateName.LISTENING, "Понял запрос, можно отвечать.")
            return True

        last_intent_key = intent_key
        return False

    return should_stop


def _needs_confirmation(transcription: TranscriptionResult) -> bool:
    if transcription.avg_logprob is not None and transcription.avg_logprob < STT_CONFIRMATION_LOGPROB_THRESHOLD:
        return True
    if (
        transcription.no_speech_prob is not None
        and transcription.no_speech_prob > STT_CONFIRMATION_NO_SPEECH_THRESHOLD
    ):
        return True
    return False


def _thinking_message_for(user_text: str) -> str:
    if generate_local_chat_reply(
        user_text,
        history_size=len(conversation_memory.recent()),
        tone="child" if child_mode_store.is_enabled() else conversation_tone.current(),
        child_mode=child_mode_store.is_enabled(),
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
    speak(f"Я расслышал так: {candidate_text}. Если все верно, скажи да. Иначе повтори фразу еще раз.")
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
