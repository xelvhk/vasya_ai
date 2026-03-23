from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write


@dataclass(frozen=True)
class RecordingResult:
    filename: str
    rms: float


def record_audio(filename: str, duration: int, samplerate: int = 44100) -> RecordingResult:
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
