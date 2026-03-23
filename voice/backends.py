from __future__ import annotations

import subprocess
from dataclasses import dataclass

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

from config.settings import TTS_BACKEND, TTS_RATE, TTS_VOICE, VOICE_INPUT_BACKEND
from utils.platform_runtime import get_platform_name


@dataclass(frozen=True)
class RecordingResult:
    filename: str
    rms: float


class BaseTTSBackend:
    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        raise NotImplementedError

    def list_voices(self) -> list[str]:
        return []


class MacOSTTSBackend(BaseTTSBackend):
    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        selected_voice = voice or TTS_VOICE
        selected_rate = rate or TTS_RATE

        command = ["say", "-v", selected_voice, "-r", str(selected_rate), text]
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            subprocess.run(["say", "-r", str(selected_rate), text], check=False)

    def list_voices(self) -> list[str]:
        result = subprocess.run(
            ["say", "-v", "?"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return []

        voices = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            voice_name = stripped.split("#", maxsplit=1)[0].rsplit(maxsplit=1)[0].strip()
            voices.append(voice_name)
        return voices


class PrintTTSBackend(BaseTTSBackend):
    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        _ = voice, rate
        print(f"[TTS fallback] {text}")


class BaseVoiceInputBackend:
    def record(self, filename: str, duration: int, samplerate: int = 44100) -> RecordingResult:
        raise NotImplementedError


class SoundDeviceVoiceInputBackend(BaseVoiceInputBackend):
    def record(self, filename: str, duration: int, samplerate: int = 44100) -> RecordingResult:
        print("Слушаю...")
        recording = sd.rec(
            int(duration * samplerate),
            samplerate=samplerate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        write(filename, samplerate, recording)

        float_audio = recording.astype("float32")
        rms = float(np.sqrt(np.mean(np.square(float_audio))))
        return RecordingResult(filename=filename, rms=rms)


def get_tts_backend() -> BaseTTSBackend:
    backend_name = TTS_BACKEND.lower()
    platform_name = get_platform_name()

    if backend_name == "print":
        return PrintTTSBackend()
    if backend_name == "say":
        return MacOSTTSBackend()
    if backend_name == "auto":
        if platform_name == "macos":
            return MacOSTTSBackend()
        return PrintTTSBackend()

    return PrintTTSBackend()


def get_voice_input_backend() -> BaseVoiceInputBackend:
    backend_name = VOICE_INPUT_BACKEND.lower()

    if backend_name in ("auto", "sounddevice"):
        return SoundDeviceVoiceInputBackend()

    return SoundDeviceVoiceInputBackend()
