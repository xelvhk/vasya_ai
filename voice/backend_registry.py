from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.orchestrator import process_text_detailed
from services.chat_service import generate_chat_reply
from voice.stt import transcribe
from voice.tts import speak


class STTBackend(Protocol):
    backend_id: str

    def transcribe(self, audio_path: str) -> str:
        ...


class TTSBackend(Protocol):
    backend_id: str

    def speak(self, text: str) -> None:
        ...


class LLMBackend(Protocol):
    backend_id: str

    def respond(self, text: str) -> str:
        ...


@dataclass(frozen=True)
class DefaultSTTBackend:
    backend_id: str = "stt.default.faster_whisper"

    def transcribe(self, audio_path: str) -> str:
        return transcribe(audio_path).text


@dataclass(frozen=True)
class DefaultTTSBackend:
    backend_id: str = "tts.default.runtime_selected"

    def speak(self, text: str) -> None:
        speak(text)


@dataclass(frozen=True)
class DefaultLLMBackend:
    backend_id: str = "llm.default.orchestrator"

    def respond(self, text: str) -> str:
        return process_text_detailed(text).response


@dataclass(frozen=True)
class ChatLLMBackend:
    backend_id: str = "llm.chat.local"

    def respond(self, text: str) -> str:
        return generate_chat_reply(text)


_STT_REGISTRY: dict[str, STTBackend] = {
    "default": DefaultSTTBackend(),
}
_TTS_REGISTRY: dict[str, TTSBackend] = {
    "default": DefaultTTSBackend(),
}
_LLM_REGISTRY: dict[str, LLMBackend] = {
    "default": DefaultLLMBackend(),
    "chat": ChatLLMBackend(),
}


def register_stt_backend(name: str, backend: STTBackend) -> None:
    _STT_REGISTRY[name] = backend


def register_tts_backend(name: str, backend: TTSBackend) -> None:
    _TTS_REGISTRY[name] = backend


def register_llm_backend(name: str, backend: LLMBackend) -> None:
    _LLM_REGISTRY[name] = backend


def get_stt_backend(name: str = "default") -> STTBackend:
    return _STT_REGISTRY.get(name, _STT_REGISTRY["default"])


def get_tts_backend(name: str = "default") -> TTSBackend:
    return _TTS_REGISTRY.get(name, _TTS_REGISTRY["default"])


def get_llm_backend(name: str = "default") -> LLMBackend:
    return _LLM_REGISTRY.get(name, _LLM_REGISTRY["default"])


def list_backend_registry() -> dict[str, list[str]]:
    return {
        "stt": sorted(_STT_REGISTRY.keys()),
        "tts": sorted(_TTS_REGISTRY.keys()),
        "llm": sorted(_LLM_REGISTRY.keys()),
    }
