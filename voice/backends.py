from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import read as read_wav
from scipy.io.wavfile import write

from config.settings import (
    PIPER_COMMAND,
    PIPER_LENGTH_SCALE,
    PIPER_MODEL_PATH,
    PIPER_SPEAKER,
    TTS_BACKEND,
    TTS_RATE,
    TTS_VOICE,
    VOICE_INPUT_BACKEND,
)
from utils.platform_runtime import get_platform_name


@dataclass(frozen=True)
class RecordingResult:
    filename: str
    rms: float


class BaseTTSBackend:
    name = "unknown"

    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        raise NotImplementedError

    def list_voices(self) -> list[str]:
        return []

    def stop(self) -> None:
        return None

    def is_speaking(self) -> bool:
        return False


class MacOSTTSBackend(BaseTTSBackend):
    name = "say"

    def __init__(self) -> None:
        self._lock = Lock()
        self._process: subprocess.Popen[str] | None = None
        self._interrupted = False

    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        selected_voice = voice or TTS_VOICE
        selected_rate = rate or TTS_RATE

        command = ["say", "-v", selected_voice, "-r", str(selected_rate), text]
        with self._lock:
            self._interrupted = False
        process = subprocess.Popen(command)
        with self._lock:
            self._process = process
        return_code = process.wait()
        with self._lock:
            interrupted = self._interrupted
            if self._process is process:
                self._process = None

        if return_code != 0 and not interrupted:
            fallback_process = subprocess.Popen(["say", "-r", str(selected_rate), text])
            with self._lock:
                self._process = fallback_process
            fallback_process.wait()
            with self._lock:
                if self._process is fallback_process:
                    self._process = None
                self._interrupted = False

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
            self._interrupted = True
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
    name = "print"

    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        _ = voice, rate
        print(f"[TTS fallback] {text}")


class PiperTTSBackend(BaseTTSBackend):
    name = "piper"

    def __init__(self) -> None:
        self._lock = Lock()
        self._tts_process: subprocess.Popen[str] | None = None
        self._play_process: subprocess.Popen[str] | None = None
        self._is_playing = False

    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        _ = voice, rate
        if not PIPER_MODEL_PATH:
            raise RuntimeError("PIPER_MODEL_PATH is not configured.")
        command_path = _resolve_piper_command()
        if command_path is None:
            raise RuntimeError(f"Piper command '{PIPER_COMMAND}' was not found.")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            output_path = Path(temp_file.name)

        command = [
            command_path,
            "--model",
            PIPER_MODEL_PATH,
            "--output_file",
            str(output_path),
        ]
        if PIPER_SPEAKER:
            command.extend(["--speaker", PIPER_SPEAKER])
        if PIPER_LENGTH_SCALE:
            command.extend(["--length_scale", PIPER_LENGTH_SCALE])

        tts_process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            text=True,
        )
        with self._lock:
            self._tts_process = tts_process
        try:
            tts_process.communicate(text, timeout=60)
        finally:
            with self._lock:
                if self._tts_process is tts_process:
                    self._tts_process = None

        if not output_path.exists():
            return

        try:
            self._play_audio_file(output_path)
        finally:
            with self._lock:
                self._is_playing = False
            output_path.unlink(missing_ok=True)

    def stop(self) -> None:
        with self._lock:
            tts_process = self._tts_process
        if tts_process is not None and tts_process.poll() is None:
            tts_process.terminate()
            try:
                tts_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                tts_process.kill()
        sd.stop()
        with self._lock:
            play_process = self._play_process
        if play_process is not None and play_process.poll() is None:
            play_process.terminate()
            try:
                play_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                play_process.kill()
        with self._lock:
            self._tts_process = None
            self._play_process = None
            self._is_playing = False

    def is_speaking(self) -> bool:
        with self._lock:
            tts_process = self._tts_process
            play_process = self._play_process
            is_playing = self._is_playing
        return (
            (tts_process is not None and tts_process.poll() is None)
            or (play_process is not None and play_process.poll() is None)
            or is_playing
        )

    def _play_audio_file(self, output_path: Path) -> None:
        if get_platform_name() == "macos" and self._play_with_afplay(output_path):
            return

        try:
            sample_rate, audio_data = read_wav(str(output_path))
            if audio_data.dtype.kind in ("i", "u"):
                max_value = max(abs(np.iinfo(audio_data.dtype).min), np.iinfo(audio_data.dtype).max)
                audio_data = audio_data.astype(np.float32) / float(max_value)
            else:
                audio_data = audio_data.astype(np.float32)

            if audio_data.ndim > 1 and audio_data.shape[1] == 1:
                audio_data = audio_data.reshape(-1)

            with self._lock:
                self._is_playing = True
            sd.play(audio_data, sample_rate)
            sd.wait()
            return
        except Exception:
            sd.stop()

        if self._play_with_afplay(output_path):
            return

        print("[Piper playback error] Unable to play generated audio")

    def _play_with_afplay(self, output_path: Path) -> bool:
        try:
            play_process = subprocess.Popen(["afplay", str(output_path)])
            with self._lock:
                self._play_process = play_process
                self._is_playing = True
            play_process.wait(timeout=120)
            return play_process.returncode == 0
        except Exception as exc:
            print(f"[Piper playback error] {exc}")
            return False
        finally:
            with self._lock:
                self._play_process = None


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
    if backend_name == "piper":
        _TTS_BACKEND = PiperTTSBackend()
        return _TTS_BACKEND
    if backend_name == "say":
        _TTS_BACKEND = MacOSTTSBackend()
        return _TTS_BACKEND
    if backend_name == "auto":
        if is_piper_available():
            _TTS_BACKEND = PiperTTSBackend()
            return _TTS_BACKEND
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


def is_piper_available() -> bool:
    return bool(PIPER_MODEL_PATH) and _resolve_piper_command() is not None


def get_tts_backend_name() -> str:
    return get_tts_backend().name


def get_tts_backend_status() -> str:
    configured_backend = TTS_BACKEND.lower()
    active_backend = get_tts_backend_name()

    if configured_backend == "auto":
        if active_backend == "piper":
            return f"TTS backend: piper ({Path(PIPER_MODEL_PATH).name})"
        if active_backend == "say":
            return f"TTS backend: say ({TTS_VOICE})"
        return f"TTS backend: {active_backend}"

    if configured_backend == "piper" and not is_piper_available():
        if not PIPER_MODEL_PATH:
            return "TTS backend: piper is selected, but PIPER_MODEL_PATH is not configured"
        return f"TTS backend: piper is selected, but command '{PIPER_COMMAND}' was not found"

    if active_backend == "piper":
        return f"TTS backend: piper ({Path(PIPER_MODEL_PATH).name})"
    if active_backend == "say":
        return f"TTS backend: say ({TTS_VOICE})"
    return f"TTS backend: {active_backend}"


def _resolve_piper_command() -> str | None:
    if Path(PIPER_COMMAND).expanduser().exists():
        return str(Path(PIPER_COMMAND).expanduser())

    command_from_path = shutil.which(PIPER_COMMAND)
    if command_from_path is not None:
        return command_from_path

    virtual_env = os.getenv("VIRTUAL_ENV")
    if virtual_env:
        sibling_command = Path(virtual_env) / "bin" / "piper"
        if sibling_command.exists():
            return str(sibling_command)

    sibling_command = Path(sys.executable).parent / "piper"
    if sibling_command.exists():
        return str(sibling_command)

    return None
