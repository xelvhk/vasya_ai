import sounddevice as sd
from scipy.io.wavfile import write

def record_audio(filename: str, duration: int, samplerate: int = 44100) -> None:
    print("Слушаю...")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype="int16")
    sd.wait()
    write(filename, samplerate, recording)