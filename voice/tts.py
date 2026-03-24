import argparse
import re

from voice.backends import get_tts_backend, get_tts_backend_status


_BACKEND_STATUS_PRINTED = False


def speak(text: str, voice: str | None = None, rate: int | None = None) -> None:
    global _BACKEND_STATUS_PRINTED
    print(f"Vasya: {text}")

    if not text.strip():
        return

    if not _BACKEND_STATUS_PRINTED:
        print(get_tts_backend_status())
        _BACKEND_STATUS_PRINTED = True

    backend = get_tts_backend()
    backend.speak(_prepare_text_for_speech(text), voice=voice, rate=rate)


def _prepare_text_for_speech(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        normalized = re.sub(r"^\s*\d+\.\s+", "", line).strip()
        if normalized:
            cleaned_lines.append(normalized)
    return ". ".join(cleaned_lines) if cleaned_lines else text.strip()


def list_voices() -> list[str]:
    backend = get_tts_backend()
    return backend.list_voices()


def stop_speaking() -> None:
    backend = get_tts_backend()
    backend.stop()


def is_speaking() -> bool:
    backend = get_tts_backend()
    return backend.is_speaking()


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
