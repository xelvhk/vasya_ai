from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from queue import Queue, Empty
from typing import Callable

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import read as read_wav
from scipy.io.wavfile import write

from config.settings import (
    COSYVOICE_MODEL_DIR,
    COSYVOICE_PROMPT_TEXT,
    COSYVOICE_PROMPT_WAV,
    COSYVOICE_PYTHON,
    COSYVOICE_REPO_DIR,
    COSYVOICE_SPEAKER,
    COSYVOICE_TIMEOUT_SECONDS,
    MIN_AUDIO_RMS,
    PIPER_COMMAND,
    PIPER_LENGTH_SCALE,
    PIPER_MODEL_PATH,
    PIPER_SPEAKER,
    TTS_BACKEND,
    TTS_HYBRID_SHORT_TEXT_MAX_WORDS,
    TTS_RATE,
    TTS_RUNTIME_MODE,
    TTS_VOICE,
    TTS_CACHE_DIR,
    VOICE_EARLY_FAST_INTENT_ENABLED,
    VOICE_EARLY_FAST_INTENT_MIN_REPEATS,
    VOICE_MIN_SPEECH_SECONDS,
    VOICE_PARTIAL_STT_ENABLED,
    VOICE_PARTIAL_STT_INTERVAL_SECONDS,
    VOICE_SILENCE_DURATION_SECONDS,
    VOICE_SILENCE_RMS,
    VOICE_START_TIMEOUT_SECONDS,
    VOICE_INPUT_BACKEND,
    XTTS_COMMAND,
    XTTS_LANGUAGE,
    XTTS_MODEL_NAME,
    XTTS_SPEAKER_WAV,
    XTTS_TIMEOUT_SECONDS,
    XTTS_SPEED,
)
from utils.platform_runtime import get_platform_name
from voice.profiles import (
    VoiceProfile,
    get_active_voice_profile,
    get_profile_model_path,
    get_profile_speaker_wav,
    get_voice_profile,
    is_profile_installed,
    list_voice_profiles,
)


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
        profile = _resolve_voice_profile(voice)
        selected_voice = voice if voice and voice not in _VOICE_PROFILE_IDS else None
        selected_voice = selected_voice or profile.say_voice or TTS_VOICE
        selected_rate = rate or profile.say_rate or TTS_RATE

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
        profile_labels = [profile.label for profile in list_voice_profiles()]
        result = subprocess.run(
            ["say", "-v", "?"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return profile_labels

        voices = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            voice_name = stripped.split("#", maxsplit=1)[0].rsplit(maxsplit=1)[0].strip()
            voices.append(voice_name)
        return profile_labels + voices

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
        profile = _resolve_voice_profile(voice)
        model_path = get_profile_model_path(profile)
        if model_path is None:
            raise RuntimeError(f"Piper model for profile '{profile.label}' is not available.")
        command_path = _resolve_piper_command()
        if command_path is None:
            raise RuntimeError(f"Piper command '{PIPER_COMMAND}' was not found.")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            output_path = Path(temp_file.name)

        command = [
            command_path,
            "--model",
            str(model_path),
            "--output_file",
            str(output_path),
        ]
        if PIPER_SPEAKER:
            command.extend(["--speaker", PIPER_SPEAKER])
        length_scale = profile.piper_length_scale
        if length_scale is None and PIPER_LENGTH_SCALE:
            length_scale = float(PIPER_LENGTH_SCALE)
        if length_scale is not None:
            command.extend(["--length_scale", str(length_scale)])

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

    def list_voices(self) -> list[str]:
        voices = []
        for profile in list_voice_profiles():
            if profile.backend != "piper":
                continue
            suffix = "" if is_profile_installed(profile) else " (нужно скачать)"
            voices.append(f"{profile.label}{suffix}")
        return voices

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


class XTTSBackend(BaseTTSBackend):
    name = "xtts"

    def __init__(self) -> None:
        self._lock = Lock()
        self._tts_process: subprocess.Popen[str] | None = None
        self._play_process: subprocess.Popen[str] | None = None
        self._is_playing = False

    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        _ = rate
        profile = _resolve_voice_profile(voice)
        if profile.backend != "xtts":
            raise RuntimeError("XTTS backend expects an xtts profile.")
        command_path = _resolve_command(XTTS_COMMAND)
        if command_path is None:
            raise RuntimeError(f"XTTS command '{XTTS_COMMAND}' was not found.")
        speaker_wav = get_profile_speaker_wav(profile)
        if speaker_wav is None:
            raise RuntimeError(
                f"XTTS speaker sample for profile '{profile.label}' is not configured. "
                "Set XTTS_SPEAKER_WAV in .env or choose a piper profile."
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            output_path = Path(temp_file.name)
        xtts_cache_dir = Path("storage/xtts_cache").resolve()
        mpl_cache_dir = Path("storage/mpl_cache").resolve()
        xtts_cache_dir.mkdir(parents=True, exist_ok=True)
        mpl_cache_dir.mkdir(parents=True, exist_ok=True)

        language = (profile.xtts_language or XTTS_LANGUAGE or "ru").strip() or "ru"
        command = [
            command_path,
            "--model_name",
            XTTS_MODEL_NAME,
            "--text",
            text,
            "--speaker_wav",
            str(speaker_wav),
            "--language_idx",
            language,
            "--out_path",
            str(output_path),
        ]

        hf_cache_dir = xtts_cache_dir / "hf_cache"
        hf_cache_dir.mkdir(parents=True, exist_ok=True)
        xtts_env = {
            **os.environ,
            "TTS_HOME": str(xtts_cache_dir),
            "XDG_DATA_HOME": str(xtts_cache_dir),
            "MPLCONFIGDIR": str(mpl_cache_dir),
            "COQUI_TOS_AGREED": "1",
        }
        # Coqui XTTS + newer PyTorch requires explicit opt-out from weights-only load.
        xtts_env.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
        # Keep HuggingFace cache inside project storage to avoid permission issues.
        xtts_env.setdefault("HF_HOME", str(hf_cache_dir))

        tts_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=xtts_env,
        )
        with self._lock:
            self._tts_process = tts_process
        try:
            _stdout, stderr = tts_process.communicate(timeout=max(120, XTTS_TIMEOUT_SECONDS))
            if tts_process.returncode != 0:
                raise RuntimeError((stderr or "").strip() or "XTTS synthesis failed.")
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

    def list_voices(self) -> list[str]:
        voices = []
        for profile in list_voice_profiles():
            if profile.backend != "xtts":
                continue
            suffix = "" if is_profile_installed(profile) else " (нужно указать XTTS_SPEAKER_WAV)"
            voices.append(f"{profile.label}{suffix}")
        return voices

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

        print("[XTTS playback error] Unable to play generated audio")

    def _play_with_afplay(self, output_path: Path) -> bool:
        try:
            play_process = subprocess.Popen(["afplay", str(output_path)])
            with self._lock:
                self._play_process = play_process
                self._is_playing = True
            play_process.wait(timeout=120)
            return play_process.returncode == 0
        except Exception as exc:
            print(f"[XTTS playback error] {exc}")
            return False
        finally:
            with self._lock:
                self._play_process = None


class CosyVoiceTTSBackend(BaseTTSBackend):
    name = "cosyvoice"

    def __init__(self) -> None:
        self._lock = Lock()
        self._tts_process: subprocess.Popen[str] | None = None
        self._play_process: subprocess.Popen[str] | None = None
        self._is_playing = False

    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        _ = voice, rate
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            output_path = Path(temp_file.name)

        try:
            command, cosyvoice_env = self._build_command(text=text, output_path=output_path)
            tts_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=cosyvoice_env,
            )
            with self._lock:
                self._tts_process = tts_process
            try:
                _stdout, stderr = tts_process.communicate(timeout=COSYVOICE_TIMEOUT_SECONDS)
                if tts_process.returncode != 0:
                    raise RuntimeError((stderr or "").strip() or "CosyVoice synthesis failed.")
            finally:
                with self._lock:
                    if self._tts_process is tts_process:
                        self._tts_process = None

            if output_path.exists():
                self._play_audio_file(output_path)
        finally:
            with self._lock:
                self._is_playing = False
            output_path.unlink(missing_ok=True)

    def _build_command(self, *, text: str, output_path: Path) -> tuple[list[str], dict[str, str]]:
        repo_dir = Path(COSYVOICE_REPO_DIR).expanduser() if COSYVOICE_REPO_DIR else None
        model_dir = Path(COSYVOICE_MODEL_DIR).expanduser() if COSYVOICE_MODEL_DIR else None
        if repo_dir is None or not repo_dir.exists():
            raise RuntimeError("CosyVoice repo is not configured. Set COSYVOICE_REPO_DIR.")
        if model_dir is None or not model_dir.exists():
            raise RuntimeError("CosyVoice model is not configured. Set COSYVOICE_MODEL_DIR.")
        python_path = _resolve_python_command(COSYVOICE_PYTHON)
        if python_path is None:
            raise RuntimeError(f"CosyVoice Python was not found: {COSYVOICE_PYTHON}")

        script_path = Path(__file__).resolve().parent.parent / "scripts" / "run_cosyvoice_tts.py"
        command = [
            python_path,
            str(script_path),
            "--repo-dir",
            str(repo_dir),
            "--model-dir",
            str(model_dir),
            "--text",
            text,
            "--output",
            str(output_path),
        ]
        prompt_wav = _cosyvoice_prompt_wav()
        if (model_dir / "cosyvoice3.yaml").exists():
            if prompt_wav is None:
                raise RuntimeError("CosyVoice3 requires COSYVOICE_PROMPT_WAV or XTTS_SPEAKER_WAV.")
            command.extend(["--prompt-wav", str(prompt_wav), "--prompt-text", COSYVOICE_PROMPT_TEXT])
        if COSYVOICE_SPEAKER:
            command.extend(["--speaker", COSYVOICE_SPEAKER])

        cache_dir = Path(TTS_CACHE_DIR).expanduser()
        if not cache_dir.is_absolute():
            cache_dir = Path(__file__).resolve().parent.parent / cache_dir
        cosyvoice_cache_dir = cache_dir / "cosyvoice"
        hf_cache_dir = cosyvoice_cache_dir / "hf_home"
        mpl_cache_dir = Path(__file__).resolve().parent.parent / "storage" / "mpl_cache"
        for cache_path in (cosyvoice_cache_dir, hf_cache_dir, mpl_cache_dir):
            cache_path.mkdir(parents=True, exist_ok=True)
        cosyvoice_env = {
            **os.environ,
            "XDG_CACHE_HOME": str(cosyvoice_cache_dir),
            "HF_HOME": str(hf_cache_dir),
            "MPLCONFIGDIR": str(mpl_cache_dir),
            "TOKENIZERS_PARALLELISM": "false",
        }
        return command, cosyvoice_env

    def list_voices(self) -> list[str]:
        suffix = "" if is_cosyvoice_available() else " (нужно настроить CosyVoice3)"
        return [f"Вася — красивый CosyVoice3{suffix}"]

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

        print("[CosyVoice playback error] Unable to play generated audio")

    def _play_with_afplay(self, output_path: Path) -> bool:
        try:
            play_process = subprocess.Popen(["afplay", str(output_path)])
            with self._lock:
                self._play_process = play_process
                self._is_playing = True
            play_process.wait(timeout=120)
            return play_process.returncode == 0
        except Exception as exc:
            print(f"[CosyVoice playback error] {exc}")
            return False
        finally:
            with self._lock:
                self._play_process = None


class HybridTTSBackend(BaseTTSBackend):
    name = "hybrid"

    def __init__(self) -> None:
        self._piper = PiperTTSBackend()
        self._xtts = XTTSBackend()

    def speak(self, text: str, voice: str | None = None, rate: int | None = None) -> None:
        words = [word for word in text.split() if word.strip()]
        use_fast = len(words) <= max(1, TTS_HYBRID_SHORT_TEXT_MAX_WORDS)
        profile = _resolve_voice_profile(voice)
        if profile.backend == "piper":
            self._piper.speak(text, voice=voice, rate=rate)
            return
        if profile.backend == "xtts":
            if use_fast and is_piper_available():
                try:
                    self._piper.speak(text, voice="ruslan_direct", rate=rate)
                    return
                except Exception:
                    pass
            self._xtts.speak(text, voice=voice, rate=rate)
            return

        if use_fast and is_piper_available():
            self._piper.speak(text, voice=voice, rate=rate)
            return
        self._xtts.speak(text, voice=voice, rate=rate)

    def list_voices(self) -> list[str]:
        return self._piper.list_voices() + self._xtts.list_voices()

    def stop(self) -> None:
        self._piper.stop()
        self._xtts.stop()

    def is_speaking(self) -> bool:
        return self._piper.is_speaking() or self._xtts.is_speaking()


_TTS_BACKEND: BaseTTSBackend | None = None
_VOICE_PROFILE_IDS = {profile.profile_id for profile in list_voice_profiles()}


class BaseVoiceInputBackend:
    def record(
        self,
        filename: str,
        duration: int,
        samplerate: int = 44100,
        status_callback: Callable[[str], None] | None = None,
        partial_text_callback: Callable[[str], None] | None = None,
        early_stop_callback: Callable[[str], bool] | None = None,
    ) -> RecordingResult:
        raise NotImplementedError


class SoundDeviceVoiceInputBackend(BaseVoiceInputBackend):
    def record(
        self,
        filename: str,
        duration: int,
        samplerate: int = 44100,
        status_callback: Callable[[str], None] | None = None,
        partial_text_callback: Callable[[str], None] | None = None,
        early_stop_callback: Callable[[str], bool] | None = None,
    ) -> RecordingResult:
        print("Слушаю...")
        block_duration = 0.1
        blocksize = int(samplerate * block_duration)
        max_blocks = max(1, int(duration / block_duration))
        silence_blocks_to_stop = max(1, int(VOICE_SILENCE_DURATION_SECONDS / block_duration))
        min_speech_blocks = max(1, int(VOICE_MIN_SPEECH_SECONDS / block_duration))
        partial_interval_blocks = max(1, int(VOICE_PARTIAL_STT_INTERVAL_SECONDS / block_duration))
        start_timeout_blocks = max(1, int(VOICE_START_TIMEOUT_SECONDS / block_duration))

        audio_queue: Queue[np.ndarray | None] = Queue()
        collected_blocks: list[np.ndarray] = []
        silence_blocks = 0
        speech_blocks = 0
        speech_started = False
        last_partial_block = 0
        last_partial_text = ""
        stable_partial_repeats = 0

        def callback(indata, frames, time_info, status) -> None:
            _ = frames, time_info, status
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=samplerate,
            channels=1,
            dtype="int16",
            blocksize=blocksize,
            callback=callback,
        ):
            for _ in range(max_blocks):
                try:
                    block = audio_queue.get(timeout=1.0)
                except Empty:
                    break

                if block is None:
                    break

                collected_blocks.append(block)
                float_block = block.astype("float32")
                block_rms = float(np.sqrt(np.mean(np.square(float_block))))

                if not speech_started and block_rms < VOICE_SILENCE_RMS:
                    silence_blocks += 1
                    if silence_blocks >= start_timeout_blocks:
                        break
                    continue

                if block_rms >= VOICE_SILENCE_RMS:
                    if not speech_started and status_callback is not None:
                        status_callback("Слышу тебя, договаривай...")
                    speech_started = True
                    speech_blocks += 1
                    silence_blocks = 0
                    if (
                        partial_text_callback is not None
                        and VOICE_PARTIAL_STT_ENABLED
                        and speech_blocks >= min_speech_blocks
                        and speech_blocks - last_partial_block >= partial_interval_blocks
                    ):
                        partial_text = self._build_partial_transcript(
                            collected_blocks,
                            samplerate,
                        )
                        last_partial_block = speech_blocks
                        if partial_text and partial_text != last_partial_text:
                            partial_text_callback(partial_text)
                            last_partial_text = partial_text
                            stable_partial_repeats = 1
                        elif partial_text and partial_text == last_partial_text:
                            stable_partial_repeats += 1

                        if (
                            partial_text
                            and VOICE_EARLY_FAST_INTENT_ENABLED
                            and early_stop_callback is not None
                            and stable_partial_repeats >= VOICE_EARLY_FAST_INTENT_MIN_REPEATS
                            and early_stop_callback(partial_text)
                        ):
                            break
                elif speech_started:
                    silence_blocks += 1
                    if speech_blocks >= min_speech_blocks and silence_blocks >= silence_blocks_to_stop:
                        break

        if collected_blocks:
            recording = np.concatenate(collected_blocks, axis=0)
        else:
            recording = np.zeros((0, 1), dtype="int16")

        write(filename, samplerate, recording)

        float_audio = recording.astype("float32") if recording.size else np.zeros((0, 1), dtype="float32")
        rms = (
            float(np.sqrt(np.mean(np.square(float_audio))))
            if float_audio.size
            else 0.0
        )
        return RecordingResult(filename=filename, rms=rms)

    def _build_partial_transcript(
        self,
        collected_blocks: list[np.ndarray],
        samplerate: int,
    ) -> str:
        if not collected_blocks:
            return ""

        from voice.stt import transcribe_partial

        recording = np.concatenate(collected_blocks, axis=0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        try:
            write(str(temp_path), samplerate, recording)
            return transcribe_partial(str(temp_path))
        except Exception:
            return ""
        finally:
            temp_path.unlink(missing_ok=True)


def get_tts_backend() -> BaseTTSBackend:
    global _TTS_BACKEND
    if _TTS_BACKEND is not None:
        return _TTS_BACKEND

    backend_name = TTS_BACKEND.lower()

    if backend_name == "print":
        _TTS_BACKEND = PrintTTSBackend()
        return _TTS_BACKEND
    if backend_name == "piper":
        _TTS_BACKEND = PiperTTSBackend()
        return _TTS_BACKEND
    if backend_name == "xtts":
        _TTS_BACKEND = XTTSBackend()
        return _TTS_BACKEND
    if backend_name == "cosyvoice":
        _TTS_BACKEND = CosyVoiceTTSBackend()
        return _TTS_BACKEND
    if backend_name == "hybrid":
        _TTS_BACKEND = HybridTTSBackend()
        return _TTS_BACKEND
    if backend_name == "say":
        _TTS_BACKEND = MacOSTTSBackend()
        return _TTS_BACKEND
    if backend_name == "auto":
        active_profile = get_active_voice_profile()
        if TTS_RUNTIME_MODE == "quality" and is_cosyvoice_available():
            _TTS_BACKEND = CosyVoiceTTSBackend()
            return _TTS_BACKEND
        if active_profile.backend == "cosyvoice" and is_cosyvoice_available():
            _TTS_BACKEND = CosyVoiceTTSBackend()
            return _TTS_BACKEND
        if active_profile.backend == "xtts" and is_xtts_available(active_profile):
            _TTS_BACKEND = HybridTTSBackend()
            return _TTS_BACKEND
        if is_piper_available():
            _TTS_BACKEND = PiperTTSBackend()
            return _TTS_BACKEND
        if active_profile.backend == "xtts" and is_xtts_command_available():
            _TTS_BACKEND = XTTSBackend()
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
    return get_profile_model_path() is not None and _resolve_piper_command() is not None


def is_xtts_command_available() -> bool:
    return _resolve_command(XTTS_COMMAND) is not None


def is_xtts_available(profile: VoiceProfile | None = None) -> bool:
    return is_xtts_command_available() and get_profile_speaker_wav(profile) is not None


def is_cosyvoice_available() -> bool:
    repo_dir = Path(COSYVOICE_REPO_DIR).expanduser() if COSYVOICE_REPO_DIR else None
    model_dir = Path(COSYVOICE_MODEL_DIR).expanduser() if COSYVOICE_MODEL_DIR else None
    if repo_dir is None or not repo_dir.exists():
        return False
    if model_dir is None or not model_dir.exists():
        return False
    if (model_dir / "cosyvoice3.yaml").exists() and _cosyvoice_prompt_wav() is None:
        return False
    if COSYVOICE_PYTHON:
        return _resolve_python_command(COSYVOICE_PYTHON) is not None
    return importlib.util.find_spec("cosyvoice") is not None


def get_tts_backend_name() -> str:
    return get_tts_backend().name


def get_tts_backend_status() -> str:
    configured_backend = TTS_BACKEND.lower()
    active_backend = get_tts_backend_name()
    active_profile = get_active_voice_profile()

    if configured_backend == "auto":
        if TTS_RUNTIME_MODE == "quality" and active_backend == "piper":
            return (
                "TTS backend: piper fallback (CosyVoice quality mode is unavailable; "
                "check COSYVOICE_REPO_DIR, COSYVOICE_MODEL_DIR, COSYVOICE_PYTHON, and prompt wav)"
            )
        if active_profile.backend == "cosyvoice" and active_backend == "piper":
            return (
                f"TTS backend: piper fallback (CosyVoice profile '{active_profile.label}' is unavailable; "
                "check CosyVoice settings)"
            )
        if active_backend == "cosyvoice":
            model_dir = Path(COSYVOICE_MODEL_DIR).expanduser() if COSYVOICE_MODEL_DIR else None
            model_name = model_dir.name if model_dir is not None else "missing model"
            if TTS_RUNTIME_MODE == "quality":
                return f"TTS backend: cosyvoice quality mode ({model_name})"
            return f"TTS backend: cosyvoice profile ({active_profile.label}, {model_name})"
        if active_profile.backend == "xtts" and active_backend == "piper":
            return (
                f"TTS backend: piper fallback (XTTS profile '{active_profile.label}' is unavailable; "
                "check XTTS_SPEAKER_WAV and XTTS_COMMAND)"
            )
        if active_backend == "hybrid":
            speaker = get_profile_speaker_wav(active_profile)
            speaker_name = speaker.name if speaker is not None else "missing speaker wav"
            return (
                f"TTS backend: hybrid (XTTS + Piper, {active_profile.label}, "
                f"speaker={speaker_name})"
            )
        if active_backend == "piper":
            model_path = get_profile_model_path(active_profile)
            model_name = model_path.name if model_path is not None else "missing model"
            return f"TTS backend: piper ({active_profile.label}, {model_name})"
        if active_backend == "xtts":
            speaker = get_profile_speaker_wav(active_profile)
            speaker_name = speaker.name if speaker is not None else "missing speaker wav"
            return f"TTS backend: xtts ({active_profile.label}, speaker={speaker_name})"
        if active_backend == "say":
            return f"TTS backend: say ({active_profile.label})"
        return f"TTS backend: {active_backend}"

    if configured_backend == "piper" and not is_piper_available():
        if get_profile_model_path(active_profile) is None:
            return f"TTS backend: piper is selected, but the model for '{active_profile.label}' is not installed"
        return f"TTS backend: piper is selected, but command '{PIPER_COMMAND}' was not found"
    if configured_backend == "xtts" and not is_xtts_available(active_profile):
        if get_profile_speaker_wav(active_profile) is None:
            return (
                f"TTS backend: xtts is selected, but speaker sample for "
                f"'{active_profile.label}' is not configured"
            )
        return f"TTS backend: xtts is selected, but command '{XTTS_COMMAND}' was not found"
    if configured_backend == "cosyvoice" and not is_cosyvoice_available():
        return (
            "TTS backend: cosyvoice is selected, but local CosyVoice is not fully configured "
            "(check repo, model, python, and prompt wav)"
        )

    if active_backend == "hybrid":
        speaker = get_profile_speaker_wav(active_profile)
        speaker_name = speaker.name if speaker is not None else "missing speaker wav"
        return f"TTS backend: hybrid (XTTS + Piper, {active_profile.label}, speaker={speaker_name})"
    if active_backend == "piper":
        model_path = get_profile_model_path(active_profile)
        model_name = model_path.name if model_path is not None else "missing model"
        return f"TTS backend: piper ({active_profile.label}, {model_name})"
    if active_backend == "xtts":
        speaker = get_profile_speaker_wav(active_profile)
        speaker_name = speaker.name if speaker is not None else "missing speaker wav"
        return f"TTS backend: xtts ({active_profile.label}, speaker={speaker_name})"
    if active_backend == "cosyvoice":
        model_dir = Path(COSYVOICE_MODEL_DIR).expanduser() if COSYVOICE_MODEL_DIR else None
        model_name = model_dir.name if model_dir is not None else "missing model"
        return f"TTS backend: cosyvoice quality mode ({active_profile.label}, {model_name})"
    if active_backend == "say":
        return f"TTS backend: say ({active_profile.label})"
    return f"TTS backend: {active_backend}"


def reset_tts_backend() -> None:
    global _TTS_BACKEND
    backend = _TTS_BACKEND
    if backend is not None:
        backend.stop()
    _TTS_BACKEND = None


def _resolve_piper_command() -> str | None:
    return _resolve_command(PIPER_COMMAND)


def _resolve_python_command(configured_python: str) -> str | None:
    if not configured_python:
        return sys.executable
    candidate = Path(configured_python).expanduser()
    if candidate.exists():
        return str(candidate)
    return shutil.which(configured_python)


def _cosyvoice_prompt_wav() -> Path | None:
    for configured_path in (COSYVOICE_PROMPT_WAV, XTTS_SPEAKER_WAV):
        if not configured_path:
            continue
        candidate = Path(configured_path).expanduser()
        if candidate.exists():
            return candidate
    return None


def _resolve_command(command_name: str) -> str | None:
    if Path(command_name).expanduser().exists():
        return str(Path(command_name).expanduser())

    command_from_path = shutil.which(command_name)
    if command_from_path is not None:
        return command_from_path

    virtual_env = os.getenv("VIRTUAL_ENV")
    if virtual_env:
        sibling_command = Path(virtual_env) / "bin" / command_name
        if sibling_command.exists():
            return str(sibling_command)

    sibling_command = Path(sys.executable).parent / command_name
    if sibling_command.exists():
        return str(sibling_command)

    return None


def _resolve_voice_profile(voice: str | None = None) -> VoiceProfile:
    if voice and voice in _VOICE_PROFILE_IDS:
        return get_voice_profile(voice)
    return get_active_voice_profile()
