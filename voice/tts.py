import argparse

from voice.backends import get_tts_backend


def speak(text: str, voice: str | None = None, rate: int | None = None) -> None:
    print(f"Vasya: {text}")

    if not text.strip():
        return

    backend = get_tts_backend()
    backend.speak(text, voice=voice, rate=rate)


def list_voices() -> list[str]:
    backend = get_tts_backend()
    return backend.list_voices()


def main() -> None:
    parser = argparse.ArgumentParser(description="Vasya TTS helper")
    parser.add_argument("--list-voices", action="store_true", help="Show available voices")
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
