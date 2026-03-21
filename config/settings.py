from dotenv import load_dotenv
import os

load_dotenv()

APP_VERSION = os.getenv("APP_VERSION", "0.3.0")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
AUDIO_FILENAME = os.getenv("AUDIO_FILENAME", "input.wav")
RECORD_SECONDS = int(os.getenv("RECORD_SECONDS", "5"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
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
