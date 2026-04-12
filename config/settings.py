from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent.parent

APP_VERSION = os.getenv("APP_VERSION", "0.5.8")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_FAST_MODEL = os.getenv("OLLAMA_FAST_MODEL", OLLAMA_MODEL)
OLLAMA_REASONING_MODEL = os.getenv("OLLAMA_REASONING_MODEL", OLLAMA_MODEL)
OLLAMA_FAST_THINK = os.getenv("OLLAMA_FAST_THINK", "false").lower() == "true"
OLLAMA_FAST_TEMPERATURE = float(os.getenv("OLLAMA_FAST_TEMPERATURE", "0.1"))
OLLAMA_FAST_NUM_PREDICT = int(os.getenv("OLLAMA_FAST_NUM_PREDICT", "160"))
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "auto")
OLLAMA_CHAT_MODEL_CANDIDATES = tuple(
    candidate.strip()
    for candidate in os.getenv(
        "OLLAMA_CHAT_MODEL_CANDIDATES",
        "qwen2.5:3b,llama3.2:3b,phi3:mini,qwen2.5:1.5b,llama3.2:1b,gemma2:2b,gemma3:4b",
    ).split(",")
    if candidate.strip()
)
OLLAMA_CHAT_STREAM = os.getenv("OLLAMA_CHAT_STREAM", "true").lower() == "true"
OLLAMA_CHAT_THINK = os.getenv("OLLAMA_CHAT_THINK", "false").lower() == "true"
OLLAMA_CHAT_TEMPERATURE = float(os.getenv("OLLAMA_CHAT_TEMPERATURE", "0.25"))
OLLAMA_CHAT_NUM_PREDICT = int(os.getenv("OLLAMA_CHAT_NUM_PREDICT", "160"))
OLLAMA_CHAT_QUICK_ENABLED = os.getenv("OLLAMA_CHAT_QUICK_ENABLED", "true").lower() == "true"
OLLAMA_CHAT_QUICK_MAX_WORDS = int(os.getenv("OLLAMA_CHAT_QUICK_MAX_WORDS", "10"))
OLLAMA_CHAT_QUICK_NUM_PREDICT = int(os.getenv("OLLAMA_CHAT_QUICK_NUM_PREDICT", "96"))
OLLAMA_CHAT_QUICK_MODEL = os.getenv("OLLAMA_CHAT_QUICK_MODEL", "fast").strip().lower()
AUDIO_FILENAME = os.getenv("AUDIO_FILENAME", "input.wav")
RECORD_SECONDS = int(os.getenv("RECORD_SECONDS", "5"))
VOICE_ULTRA_FAST_MODE = os.getenv("VOICE_ULTRA_FAST_MODE", "true").lower() == "true"
VOICE_ULTRA_FAST_SKIP_CONFIRM_FOR_FAST_INTENTS = os.getenv(
    "VOICE_ULTRA_FAST_SKIP_CONFIRM_FOR_FAST_INTENTS",
    "true",
).lower() == "true"
VOICE_ULTRA_FAST_MAX_RECORD_SECONDS = float(
    os.getenv("VOICE_ULTRA_FAST_MAX_RECORD_SECONDS", "3.2")
)
VOICE_SPEED_REPORT_WINDOW = int(os.getenv("VOICE_SPEED_REPORT_WINDOW", "30"))
MORNING_SHOW_ENABLED = os.getenv("MORNING_SHOW_ENABLED", "true").lower() == "true"
MORNING_SHOW_CITY = os.getenv("MORNING_SHOW_CITY", "Moscow").strip()
MORNING_SHOW_HOUR_LIMIT = int(os.getenv("MORNING_SHOW_HOUR_LIMIT", "12"))
MORNING_SHOW_STATE_FILE = os.getenv(
    "MORNING_SHOW_STATE_FILE",
    "storage/morning_show_state.json",
).strip()
VOICE_START_TIMEOUT_SECONDS = float(os.getenv("VOICE_START_TIMEOUT_SECONDS", "2.5"))
CHAT_FOLLOWUP_MAX_TURNS = int(os.getenv("CHAT_FOLLOWUP_MAX_TURNS", "3"))
VOICE_SMART_FOLLOWUP_ENABLED = os.getenv("VOICE_SMART_FOLLOWUP_ENABLED", "true").lower() == "true"
VOICE_SMART_FOLLOWUP_LISTEN_SECONDS = float(
    os.getenv("VOICE_SMART_FOLLOWUP_LISTEN_SECONDS", "3.0")
)
VOICE_SMART_FOLLOWUP_RETRIES = int(
    os.getenv("VOICE_SMART_FOLLOWUP_RETRIES", "1")
)
VOICE_AUTO_INTERRUPT_TTS_ENABLED = os.getenv(
    "VOICE_AUTO_INTERRUPT_TTS_ENABLED",
    "true",
).lower() == "true"
VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS = float(
    os.getenv("VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS", "1.0")
)
VOICE_AUTO_INTERRUPT_ADAPTIVE_ENABLED = os.getenv(
    "VOICE_AUTO_INTERRUPT_ADAPTIVE_ENABLED",
    "true",
).lower() == "true"
VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD = float(
    os.getenv("VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD", "140.0")
)
VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD = float(
    os.getenv("VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD", "260.0")
)
VOICE_AUTO_INTERRUPT_HITS_QUIET = int(
    os.getenv("VOICE_AUTO_INTERRUPT_HITS_QUIET", "1")
)
VOICE_AUTO_INTERRUPT_HITS_NORMAL = int(
    os.getenv("VOICE_AUTO_INTERRUPT_HITS_NORMAL", "2")
)
VOICE_AUTO_INTERRUPT_HITS_NOISY = int(
    os.getenv("VOICE_AUTO_INTERRUPT_HITS_NOISY", "3")
)
INTERRUPT_LISTEN_DELAY_SECONDS = float(
    os.getenv("INTERRUPT_LISTEN_DELAY_SECONDS", "0.45")
)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
STT_QUALITY_PROFILE = os.getenv("STT_QUALITY_PROFILE", "balanced").strip().lower()
_STT_PROFILE_DEFAULTS = {
    "fast": {
        "partial_model": "base",
        "final_model": "small",
        "partial_beam": 1,
        "final_beam": 3,
    },
    "balanced": {
        "partial_model": "base",
        "final_model": "large-v3-turbo",
        "partial_beam": 1,
        "final_beam": 5,
    },
    "accurate": {
        "partial_model": "small",
        "final_model": "large-v3-turbo",
        "partial_beam": 2,
        "final_beam": 5,
    },
}
_ACTIVE_STT_PROFILE = _STT_PROFILE_DEFAULTS.get(
    STT_QUALITY_PROFILE,
    _STT_PROFILE_DEFAULTS["balanced"],
)
WHISPER_PARTIAL_MODEL = os.getenv(
    "WHISPER_PARTIAL_MODEL",
    os.getenv("WHISPER_MODEL", _ACTIVE_STT_PROFILE["partial_model"]),
)
WHISPER_FINAL_MODEL = os.getenv(
    "WHISPER_FINAL_MODEL",
    os.getenv("WHISPER_MODEL", _ACTIVE_STT_PROFILE["final_model"]),
)
MAX_VOICE_RETRIES = int(os.getenv("MAX_VOICE_RETRIES", "2"))
MIN_AUDIO_RMS = float(os.getenv("MIN_AUDIO_RMS", "150.0"))
VOICE_SILENCE_RMS = float(os.getenv("VOICE_SILENCE_RMS", "110.0"))
VOICE_SILENCE_DURATION_SECONDS = float(
    os.getenv("VOICE_SILENCE_DURATION_SECONDS", "1.0")
)
VOICE_MIN_SPEECH_SECONDS = float(os.getenv("VOICE_MIN_SPEECH_SECONDS", "0.35"))
VOICE_PARTIAL_STT_ENABLED = os.getenv("VOICE_PARTIAL_STT_ENABLED", "true").lower() == "true"
VOICE_PARTIAL_STT_INTERVAL_SECONDS = float(
    os.getenv("VOICE_PARTIAL_STT_INTERVAL_SECONDS", "0.9")
)
VOICE_EARLY_FAST_INTENT_ENABLED = (
    os.getenv("VOICE_EARLY_FAST_INTENT_ENABLED", "true").lower() == "true"
)
VOICE_EARLY_FAST_INTENT_MIN_REPEATS = int(
    os.getenv("VOICE_EARLY_FAST_INTENT_MIN_REPEATS", "2")
)
STT_BEAM_SIZE = int(os.getenv("STT_BEAM_SIZE", "5"))
STT_PARTIAL_BEAM_SIZE = int(
    os.getenv("STT_PARTIAL_BEAM_SIZE", str(_ACTIVE_STT_PROFILE["partial_beam"]))
)
STT_FINAL_BEAM_SIZE = int(
    os.getenv("STT_FINAL_BEAM_SIZE", str(_ACTIVE_STT_PROFILE["final_beam"]))
)
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "ru")
STT_PARTIAL_MAX_WORDS = int(os.getenv("STT_PARTIAL_MAX_WORDS", "6"))
STT_CONFIRMATION_LOGPROB_THRESHOLD = float(
    os.getenv("STT_CONFIRMATION_LOGPROB_THRESHOLD", "-0.9")
)
STT_CONFIRMATION_NO_SPEECH_THRESHOLD = float(
    os.getenv("STT_CONFIRMATION_NO_SPEECH_THRESHOLD", "0.45")
)
VOICE_LOG_FILE = os.getenv("VOICE_LOG_FILE", "storage/voice.log")
INTERACTION_LOG_FILE = os.getenv("INTERACTION_LOG_FILE", "storage/interactions.log")
TTS_BACKEND = os.getenv("TTS_BACKEND", "auto")
VOICE_INPUT_BACKEND = os.getenv("VOICE_INPUT_BACKEND", "auto")
HOTKEY_COMBINATION = os.getenv("HOTKEY_COMBINATION", "<cmd>+<option>+<space>")
HOTKEY_TEXT_COMBINATION = os.getenv("HOTKEY_TEXT_COMBINATION", "<cmd>+<option>+k")
HOTKEY_EXIT_COMBINATION = os.getenv("HOTKEY_EXIT_COMBINATION", "<cmd>+<option>+q")
AVATAR_IMAGE_PATH = os.getenv("AVATAR_IMAGE_PATH", "").strip()
AVATAR_SKIN = os.getenv("AVATAR_SKIN", "classic").strip()
AVATAR_SIZE = int(os.getenv("AVATAR_SIZE", "210"))
AVATAR_STATE_FILE = os.getenv("AVATAR_STATE_FILE", "storage/avatar_widget.json")
AVATAR_CUSTOM_SKIN_FILE = os.getenv(
    "AVATAR_CUSTOM_SKIN_FILE",
    "storage/avatar_custom_skin.json",
).strip()
TTS_VOICE = os.getenv("TTS_VOICE", "Milena")
TTS_RATE = int(os.getenv("TTS_RATE", "185"))
TTS_PROFILE = os.getenv("TTS_PROFILE", "ruslan_direct")
TTS_STATE_FILE = os.getenv("TTS_STATE_FILE", "storage/tts_settings.json")
CHILD_MODE_STATE_FILE = os.getenv("CHILD_MODE_STATE_FILE", "storage/child_mode.json")
USER_PROFILE_STATE_FILE = os.getenv(
    "USER_PROFILE_STATE_FILE",
    "storage/user_profile.json",
)
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
OBSIDIAN_EXPORT_NOTES_DIR = os.getenv(
    "OBSIDIAN_EXPORT_NOTES_DIR",
    "Vasya Inbox",
).strip()
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN", "").strip()
NOTION_API_BASE_URL = os.getenv("NOTION_API_BASE_URL", "https://api.notion.com/v1").strip()
NOTION_API_VERSION = os.getenv("NOTION_API_VERSION", "2022-06-28").strip()
NOTION_UPDATES_PAGE_ID = os.getenv("NOTION_UPDATES_PAGE_ID", "").strip()
GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN", "").strip()
GITHUB_API_BASE_URL = os.getenv("GITHUB_API_BASE_URL", "https://api.github.com").strip()
GITHUB_DEFAULT_REPO = os.getenv("GITHUB_DEFAULT_REPO", "").strip()
GITHUB_SYNC_STATE_FILE = os.getenv(
    "GITHUB_SYNC_STATE_FILE",
    "storage/github_notion_sync_state.json",
).strip()
GITHUB_SYNC_DEFAULT_HOURS = int(os.getenv("GITHUB_SYNC_DEFAULT_HOURS", "24"))
INTEGRATIONS_STATE_FILE = os.getenv(
    "INTEGRATIONS_STATE_FILE",
    "storage/integrations.json",
).strip()
PIPER_COMMAND = os.getenv("PIPER_COMMAND", "piper")
PIPER_MODEL_PATH = os.getenv(
    "PIPER_MODEL_PATH",
    str(_BASE_DIR / "storage" / "voices" / "ru_RU-ruslan-medium.onnx"),
)
PIPER_SPEAKER = os.getenv("PIPER_SPEAKER", "")
PIPER_LENGTH_SCALE = os.getenv("PIPER_LENGTH_SCALE", "1.0")

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
