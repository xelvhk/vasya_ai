import subprocess

from config.settings import TTS_RATE, TTS_VOICE


def speak(text: str) -> None:
    print(f"Vasya: {text}")

    if not text.strip():
        return

    command = ["say", "-v", TTS_VOICE, "-r", str(TTS_RATE), text]
    result = subprocess.run(command, check=False)

    if result.returncode != 0:
        subprocess.run(["say", "-r", str(TTS_RATE), text], check=False)
