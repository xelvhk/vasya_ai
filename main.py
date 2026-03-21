from config.settings import AUDIO_FILENAME, RECORD_SECONDS
from services.ollama_client import OllamaClientError, ensure_ollama_running
from voice.recorder import record_audio
from voice.stt import transcribe
from voice.tts import speak
from core.orchestrator import process_text

def main() -> None:
    try:
        ensure_ollama_running()
    except OllamaClientError as exc:
        message = str(exc)
        print(message)
        speak(message)
        return

    record_audio(AUDIO_FILENAME, RECORD_SECONDS)
    user_text = transcribe(AUDIO_FILENAME)

    print(f"Ты сказал: {user_text}")

    if not user_text:
        speak("Я ничего не расслышал.")
        return

    response = process_text(user_text)
    speak(response)

if __name__ == "__main__":
    main()
