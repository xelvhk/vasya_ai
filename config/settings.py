from dotenv import load_dotenv
import os

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
AUDIO_FILENAME = os.getenv("AUDIO_FILENAME", "input.wav")
RECORD_SECONDS = int(os.getenv("RECORD_SECONDS", "5"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

CALENDAR_STORAGE_FILE = "storage/calendar.json"
TASK_STORAGE_FILE = "storage/tasks.json"