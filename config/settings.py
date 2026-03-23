from dotenv import load_dotenv
import os

load_dotenv()

APP_VERSION = os.getenv("APP_VERSION", "0.3.0")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
AUDIO_FILENAME = os.getenv("AUDIO_FILENAME", "input.wav")
RECORD_SECONDS = int(os.getenv("RECORD_SECONDS", "5"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
MAX_VOICE_RETRIES = int(os.getenv("MAX_VOICE_RETRIES", "2"))
MIN_AUDIO_RMS = float(os.getenv("MIN_AUDIO_RMS", "150.0"))
STT_BEAM_SIZE = int(os.getenv("STT_BEAM_SIZE", "5"))
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "ru")
VOICE_LOG_FILE = os.getenv("VOICE_LOG_FILE", "storage/voice.log")
INTERACTION_LOG_FILE = os.getenv("INTERACTION_LOG_FILE", "storage/interactions.log")
TTS_BACKEND = os.getenv("TTS_BACKEND", "auto")
VOICE_INPUT_BACKEND = os.getenv("VOICE_INPUT_BACKEND", "auto")
HOTKEY_COMBINATION = os.getenv("HOTKEY_COMBINATION", "<ctrl>+<alt>+space")
HOTKEY_EXIT_COMBINATION = os.getenv("HOTKEY_EXIT_COMBINATION", "<ctrl>+<alt>+q")
TTS_VOICE = os.getenv("TTS_VOICE", "Milena")
TTS_RATE = int(os.getenv("TTS_RATE", "185"))

STORAGE_DB_FILE = os.getenv("STORAGE_DB_FILE", "storage/vasya.db")
CALENDAR_STORAGE_FILE = os.getenv("CALENDAR_STORAGE_FILE", "storage/calendar.json")
TASK_STORAGE_FILE = os.getenv("TASK_STORAGE_FILE", "storage/tasks.json")

GOOGLE_CALENDAR_ENABLED = os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true"
GOOGLE_CALENDAR_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CALENDAR_CREDENTIALS_FILE",
    "credentials.json",
)
GOOGLE_CALENDAR_TOKEN_FILE = os.getenv(
    "GOOGLE_CALENDAR_TOKEN_FILE",
    "storage/google_token.json",
)
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_CALENDAR_TIMEZONE = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Europe/Moscow")
GOOGLE_CALENDAR_DEFAULT_EVENT_DURATION_MINUTES = int(
    os.getenv("GOOGLE_CALENDAR_DEFAULT_EVENT_DURATION_MINUTES", "60")
)
GOOGLE_CALENDAR_SYNC_ON_READ = os.getenv(
    "GOOGLE_CALENDAR_SYNC_ON_READ",
    "true",
).lower() == "true"
GOOGLE_CALENDAR_READ_MAX_RESULTS = int(
    os.getenv("GOOGLE_CALENDAR_READ_MAX_RESULTS", "20")
)
