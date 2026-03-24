from __future__ import annotations

import subprocess
from dataclasses import dataclass
from threading import Lock

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

    def stop(self) -> None:
        return None

    def is_speaking(self) -> bool:
        return False


class MacOSTTSBackend(BaseTTSBackend):
    def __init__(self) -> None:
        self._lock = Lock()
        self._process: subprocess.Popen[str] | None = None

    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        selected_voice = voice or TTS_VOICE
        selected_rate = rate or TTS_RATE

        command = ["say", "-v", selected_voice, "-r", str(selected_rate), text]
        process = subprocess.Popen(command)
        with self._lock:
            self._process = process
        return_code = process.wait()
        with self._lock:
            if self._process is process:
                self._process = None

        if return_code != 0:
            fallback_process = subprocess.Popen(["say", "-r", str(selected_rate), text])
            with self._lock:
                self._process = fallback_process
            fallback_process.wait()
            with self._lock:
                if self._process is fallback_process:
                    self._process = None

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

    def stop(self) -> None:
        with self._lock:
            process = self._process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
        with self._lock:
            if self._process is process:
                self._process = None

    def is_speaking(self) -> bool:
        with self._lock:
            process = self._process
        return process is not None and process.poll() is None


class PrintTTSBackend(BaseTTSBackend):
    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        _ = voice, rate
        print(f"[TTS fallback] {text}")


_TTS_BACKEND: BaseTTSBackend | None = None


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
    global _TTS_BACKEND
    if _TTS_BACKEND is not None:
        return _TTS_BACKEND

    backend_name = TTS_BACKEND.lower()
    platform_name = get_platform_name()

    if backend_name == "print":
        _TTS_BACKEND = PrintTTSBackend()
        return _TTS_BACKEND
    if backend_name == "say":
        _TTS_BACKEND = MacOSTTSBackend()
        return _TTS_BACKEND
    if backend_name == "auto":
        if platform_name == "macos":
            _TTS_BACKEND = MacOSTTSBackend()
            return _TTS_BACKEND
        _TTS_BACKEND = PrintTTSBackend()
        return _TTS_BACKEND

    _TTS_BACKEND = PrintTTSBackend()
    return _TTS_BACKEND


def get_voice_input_backend() -> BaseVoiceInputBackend:
    backend_name = VOICE_INPUT_BACKEND.lower()

    if backend_name in ("auto", "sounddevice"):
        return SoundDeviceVoiceInputBackend()

    return SoundDeviceVoiceInputBackend()
