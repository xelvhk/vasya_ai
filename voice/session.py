from __future__ import annotations

import time

from dataclasses import dataclass

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
from services.game_service import is_active_game_fast_phrase
from utils.chat_fast_replies import generate_local_chat_reply
from utils.intent_fastpaths import detect_early_fast_intent, detect_fast_intent
from utils.logger import log_voice_event
from voice.recorder import record_audio
from voice.models import TranscriptionResult
from voice.stt import transcribe
from voice.tts import speak


@dataclass(frozen=True)
class CaptureOutcome:
    text: str | None
    failure_reason: str | None = None


def run_voice_interaction() -> AssistantControlAction:
    followup_turns_left = CHAT_FOLLOWUP_MAX_TURNS
    keep_conversation_open = False

    while True:
        assistant_state.set(AssistantStateName.LISTENING, "Говори, я слушаю...")
        capture = _capture_user_text()
        user_text = capture.text
        if not user_text:
            if keep_conversation_open:
                reprompt = _followup_reprompt_for(capture.failure_reason)
                if reprompt and followup_turns_left > 0:
                    assistant_state.set(AssistantStateName.SPEAKING, reprompt)
                    speak(reprompt)
                    followup_turns_left -= 1
                    time.sleep(INTERRUPT_LISTEN_DELAY_SECONDS)
                    continue
                assistant_state.set(AssistantStateName.IDLE)
                return assistant_control.consume_action()
            assistant_state.set(AssistantStateName.ERROR, "Не удалось распознать голосовую команду")
            speak(_failure_message_for(capture.failure_reason))
            assistant_state.set(AssistantStateName.IDLE)
            return assistant_control.consume_action()

        print(f"Ты сказал: {user_text}")
        assistant_state.set(AssistantStateName.THINKING, _thinking_message_for(user_text))
        result = process_text_detailed(user_text)
        response = result.response
        if response:
            assistant_state.set(AssistantStateName.SPEAKING, response)
            speak(response)

        if not result.needs_followup or followup_turns_left <= 0:
            break

        keep_conversation_open = True
        followup_turns_left -= 1
        time.sleep(INTERRUPT_LISTEN_DELAY_SECONDS)

    assistant_state.set(AssistantStateName.IDLE)
    return assistant_control.consume_action()


def _capture_user_text() -> CaptureOutcome:
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
            return CaptureOutcome(text=None, failure_reason="low_audio_level")

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
            return CaptureOutcome(text=None, failure_reason="empty_transcription")

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
                return CaptureOutcome(text=None, failure_reason="confirmation_failed")
            log_voice_event(f"transcription_confirmed text={confirmed_text!r}")
            return CaptureOutcome(text=confirmed_text)

        log_voice_event(
            "transcription_success "
            f"language={transcription.language} "
            f"avg_logprob={transcription.avg_logprob} "
            f"no_speech_prob={transcription.no_speech_prob} "
            f"text={transcription.text!r}"
        )
        return CaptureOutcome(text=transcription.text)

    log_voice_event("capture_failed reason=retries_exhausted")
    return CaptureOutcome(text=None, failure_reason="retries_exhausted")


def _update_listening_status(message: str) -> None:
    assistant_state.set(AssistantStateName.LISTENING, message)


def _update_partial_transcript(text: str) -> None:
    assistant_state.set(AssistantStateName.LISTENING, f"Похоже, ты сказал: {text}...")


def _build_early_stop_callback():
    last_intent_key: str | None = None

    def should_stop(partial_text: str) -> bool:
        nonlocal last_intent_key

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
    }


def _failure_message_for(reason: str | None) -> str:
    if reason == "low_audio_level":
        return "Было слишком тихо. Скажи еще раз чуть громче."
    if reason == "empty_transcription":
        return "Я не расслышала фразу. Попробуй сказать еще раз."
    if reason == "confirmation_failed":
        return "Я так и не разобрала фразу уверенно. Давай еще раз."
    return "Я так и не смогла нормально расслышать команду."


def _followup_reprompt_for(reason: str | None) -> str | None:
    if reason == "low_audio_level":
        return "Не расслышала. Повтори чуть громче."
    if reason == "empty_transcription":
        return "Не расслышала. Повтори, пожалуйста."
    if reason == "confirmation_failed":
        return "Не уверена, что правильно услышала. Повтори коротко."
    return None
