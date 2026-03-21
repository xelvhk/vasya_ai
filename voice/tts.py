import argparse
import subprocess

from config.settings import TTS_RATE, TTS_VOICE


def speak(text: str, voice: str | None = None, rate: int | None = None) -> None:
    print(f"Vasya: {text}")

    if not text.strip():
        return

    selected_voice = voice or TTS_VOICE
    selected_rate = rate or TTS_RATE

    command = ["say", "-v", selected_voice, "-r", str(selected_rate), text]
    result = subprocess.run(command, check=False)

    if result.returncode != 0:
        subprocess.run(["say", "-r", str(selected_rate), text], check=False)


def list_voices() -> list[str]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Vasya TTS helper")
    parser.add_argument("--list-voices", action="store_true", help="Show available macOS voices")
    parser.add_argument("--voice", help="Voice name for test playback")
    parser.add_argument("--rate", type=int, help="Speech rate for test playback")
    parser.add_argument(
        "--text",
        default="Привет, это тест озвучки Васи.",
        help="Text to speak in test mode",
    )
    args = parser.parse_args()

    if args.list_voices:
        voices = list_voices()
        for voice_name in voices:
            print(voice_name)
        return

    speak(args.text, voice=args.voice, rate=args.rate)


if __name__ == "__main__":
    main()
