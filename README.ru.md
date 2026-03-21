# Vasya AI
VAS = (Voice Ai ASsistant)
Язык: [English](README.md) | **Русский**

Локальный AI-ассистент для десктопа, голосовых команд, задач, календаря и будущих агентных сценариев.

Текущая версия: `0.3.0`

Сейчас это MVP-проект, который умеет:
- записывать голосовую команду с микрофона
- распознавать речь локально
- отправлять текст в локальную LLM через Ollama
- понимать простые команды
- добавлять задачи
- добавлять события
- разбирать базовые русские фразы даты и времени для команд календаря
- автоматически поднимать Ollama при старте, если сервер не запущен
- выбирать голос macOS для озвучки
- хранить данные локально в SQLite
- создавать события в Google Calendar при включенной интеграции

## Что уже работает

Примеры команд:
- «Добавь задачу купить лампу»
- «Какие у меня задачи»
- «Добавь встречу с Сашей завтра в 18:00»
- «Покажи события»

## Стек

- Python
- Ollama
- Llama 3
- faster-whisper
- sounddevice
- scipy
- pydantic

## Структура проекта

```text
ai_pal/
├── main.py
├── test_text.py
├── requirements.txt
├── .env
├── README.md
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── prompts.py
│
├── core/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── intent_parser.py
│   ├── router.py
│   └── models.py
│
├── voice/
│   ├── __init__.py
│   ├── recorder.py
│   ├── stt.py
│   └── tts.py
│
├── agents/
│   ├── __init__.py
│   ├── calendar_agent.py
│   └── task_agent.py
│
├── services/
│   ├── __init__.py
│   ├── ollama_client.py
│   ├── calendar_service.py
│   └── task_service.py
│
├── repositories/
│   ├── __init__.py
│   ├── event_repository.py
│   └── task_repository.py
│
├── storage/
│   ├── db.py
│   └── .gitkeep
│
└── utils/
    ├── __init__.py
    ├── datetime_parser.py
    ├── json_utils.py
    └── logger.py
```

## Как запустить

1. Клонировать проект

git clone <repo_url>
cd ai_pal

2. Создать виртуальное окружение

python3 -m venv .venv
source .venv/bin/activate

3. Установить зависимости

pip install -r requirements.txt

4. Установить и запустить Ollama

Сначала установить Ollama:

brew install ollama

Потом запустить модель:

ollama run llama3

Если модель уже скачана, достаточно просто убедиться, что Ollama доступна локально.
При старте `main.py` приложение также пытается поднять `ollama serve` автоматически.

5. Запустить проект

Проверка текстом:

python test_text.py

Запуск голосового сценария:

python main.py

## Настройки

Основные настройки лежат в config/settings.py.

Пример:

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"
AUDIO_FILENAME = "input.wav"
RECORD_SECONDS = 5
WHISPER_MODEL = "base"
TTS_VOICE = "Milena"
TTS_RATE = 185

STORAGE_DB_FILE = "storage/vasya.db"
CALENDAR_STORAGE_FILE = "storage/calendar.json"
TASK_STORAGE_FILE = "storage/tasks.json"
GOOGLE_CALENDAR_ENABLED = false
GOOGLE_CALENDAR_CREDENTIALS_FILE = "credentials.json"
GOOGLE_CALENDAR_TOKEN_FILE = "storage/google_token.json"
GOOGLE_CALENDAR_ID = "primary"
GOOGLE_CALENDAR_TIMEZONE = "Europe/Moscow"
GOOGLE_CALENDAR_DEFAULT_EVENT_DURATION_MINUTES = 60

Выбор голоса для озвучки:

Показать доступные голоса macOS:

python -m voice.tts --list-voices

Проверить конкретный голос:

python -m voice.tts --voice Milena --text "Привет, это тест озвучки"

Зафиксировать голос по умолчанию можно через `.env`:

TTS_VOICE=Milena
TTS_RATE=185

Интеграция с Google Calendar:

1. Создать OAuth Client для Desktop App в Google Cloud.
2. Скачать файл credentials и сохранить его как `credentials.json` в корне проекта.
3. Включить интеграцию через `.env`:

GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=storage/google_token.json
GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_TIMEZONE=Europe/Moscow
GOOGLE_CALENDAR_DEFAULT_EVENT_DURATION_MINUTES=60

При первом создании события откроется OAuth-авторизация Google.
Если интеграция не настроена или Google Calendar недоступен, событие все равно сохранится локально в SQLite.

## Как это работает

Pipeline сейчас такой:

Голос → запись аудио → Whisper STT → текст → Ollama → intent parsing → router → agent → локальное действие → ответ

Хранение данных

Пока данные хранятся локально:
 • задачи — в storage/vasya.db
 • события — в storage/vasya.db

Старые JSON-файлы используются только как legacy-источник для автоматической миграции в SQLite.
В репозиторий локальные данные не пушатся.

Доменный слой

Задачи и события теперь проходят через простые доменные модели и репозитории поверх SQLite.
Это упрощает сервисы и подготавливает проект к будущим интеграциям.

Ограничения текущего MVP

Сейчас проект находится на стадии MVP, поэтому есть ограничения:
 • нет wake word
 • нет постоянного прослушивания
 • нет нормальной работы с календарём через Google Calendar API
 • нет синхронизации задач с внешними сервисами
 • разбор дат пока покрывает только частые сценарии
 • нет долговременной памяти
 • нет code-agent

Что планируется дальше

Следующие возможные шаги:
 • интеграция с Obsidian / Todoist / Google Tasks
 • fallback на Piper или другой TTS-движок
 • двусторонняя синхронизация с Google Calendar
 • режим постоянного прослушивания
 • wake word «Vasya»
 • code-agent для работы с файлами и проектами
 • единое пространство для нескольких AI-агентов

## Безопасность

Проект использует локальные модели и локальное хранение данных, но при дальнейшей интеграции с внешними сервисами стоит отдельно продумать:
 • хранение токенов
 • доступ к календарю
 • доступ к файлам
 • журналирование действий агента

## Заметки

На macOS для записи звука может понадобиться доступ Terminal / IDE к микрофону:
 • System Settings
 • Privacy & Security
 • Microphone

## Автор

Xelvhk :computer:

Личный pet-project по созданию локального голосового AI-ассистента с возможностью дальнейшего расширения в систему персональных AI-агентов.
