# Vasya AI

`VAS = Voice AI Assistant`

Язык: [English](README.md) | **Русский**

Локальный voice-first AI-ассистент с текущим MVP-фокусом на macOS и дальнейшим развитием в сторону Windows и Linux.
Vasya развивается из CLI MVP в более широкую систему персонального AI: задачи, календарь, будущие сценарии для заметок, десктопный интерфейс и специализированные агенты.

Текущая версия: `0.4.0`

## Обзор

Vasya уже умеет:
- принимать голосовой ввод локально
- распознавать речь локально
- разбирать интенты через локальную LLM в Ollama
- работать с задачами
- работать с календарем
- синхронизировать события с Google Calendar
- хранить данные в локальном SQLite
- озвучивать ответы через macOS `say`
- запускаться в фоне с hotkey
- показывать первый MVP плавающего аватара на рабочем столе

Roadmap:
- см. [ROADMAP.md](ROADMAP.md)

## Текущее MVP

Сейчас проект умеет:
- записывать звук с микрофона
- транскрибировать речь локально
- маршрутизировать команды в задачи и календарь
- разбирать частые русские фразы даты и времени
- создавать, показывать, отмечать выполненными и удалять задачи
- создавать, показывать и удалять события
- фильтровать задачи и события по дате
- хранить локальные данные в SQLite
- при необходимости синхронизировать календарные события с Google Calendar
- работать в фоне и запускать голосовой цикл по горячей клавише
- показывать виджет-аватар с click-to-talk и индикацией состояний

Примеры команд:
- `Добавь задачу купить лампу`
- `Какие у меня задачи?`
- `Добавь встречу с Сашей завтра в 18:00`
- `Покажи события на 30 марта`

## Стек

- Python
- Ollama
- Llama 3
- faster-whisper
- sounddevice
- scipy
- pydantic
- SQLite

## Архитектура

Текущий pipeline:

`Голос -> запись аудио -> Whisper STT -> текст -> Ollama -> intent parsing -> router -> agent -> локальное действие -> ответ`

Модель хранения:
- задачи и события лежат в `storage/vasya.db`
- старые JSON-файлы используются только как источник миграции
- внешние интеграции подключаются как адаптеры поверх локального ядра

## Структура проекта

```text
ai_pal/
├── main.py
├── test_text.py
├── requirements.txt
├── .env
├── README.md
├── README.ru.md
├── ROADMAP.md
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
├── agents/
│   ├── __init__.py
│   ├── calendar_agent.py
│   └── task_agent.py
│
├── assistant/
│   ├── __init__.py
│   └── state.py
│
├── scripts/
│   ├── avatar_widget.py
│   ├── doctor.py
│   ├── hotkey_daemon.py
│   └── setup_mac.sh
│
├── services/
│   ├── __init__.py
│   ├── ollama_client.py
│   ├── google_calendar_client.py
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
├── voice/
│   ├── __init__.py
│   ├── recorder.py
│   ├── stt.py
│   └── tts.py
│
└── utils/
    ├── __init__.py
    ├── datetime_parser.py
    ├── humanize.py
    ├── json_utils.py
    └── logger.py
```

## Запуск

Быстрая настройка для macOS:

```bash
bash scripts/setup_mac.sh
```

Диагностика окружения:

```bash
python scripts/doctor.py
```

1. Клонировать репозиторий

```bash
git clone <repo_url>
cd ai_pal
```

2. Создать и активировать виртуальное окружение

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Установить зависимости

```bash
pip install -r requirements.txt
```

4. Установить Ollama и скачать модель

```bash
brew install ollama
ollama run llama3
```

Если Ollama уже установлена и модель доступна локально, этого достаточно.
При старте `main.py` приложение также пытается автоматически поднять `ollama serve`.

5. Запустить проект

Текстовая проверка:

```bash
python test_text.py
```

Голосовой сценарий:

```bash
python main.py
```

Фоновый режим с горячей клавишей:

```bash
python scripts/hotkey_daemon.py
```

Desktop avatar widget MVP:

```bash
python scripts/avatar_widget.py
```

Что умеет:
- левый клик запускает один голосовой цикл
- перетаскивание двигает аватар по экрану
- через `AVATAR_IMAGE_PATH` можно подставить свой PNG-аватар
- позиция виджета сохраняется между запусками
- рядом с аватаром показывается bubble во время listening, thinking, speaking и error
- правый клик закрывает виджет

Текущий платформенный фокус:
- рабочий MVP сейчас ориентирован на macOS
- в дальнейшем планируется поддержка Windows и Linux

## Конфигурация

Основные настройки находятся в `config/settings.py`.

Пример:

```env
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3
AUDIO_FILENAME=input.wav
RECORD_SECONDS=5
WHISPER_MODEL=base

TTS_VOICE=Milena
TTS_RATE=185
TTS_BACKEND=auto
VOICE_INPUT_BACKEND=auto
HOTKEY_COMBINATION=<ctrl>+<alt>+space
HOTKEY_EXIT_COMBINATION=<ctrl>+<alt>+q
AVATAR_IMAGE_PATH=
AVATAR_SIZE=140
AVATAR_STATE_FILE=storage/avatar_widget.json

STORAGE_DB_FILE=storage/vasya.db
CALENDAR_STORAGE_FILE=storage/calendar.json
TASK_STORAGE_FILE=storage/tasks.json

GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=storage/google_token.json
GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_TIMEZONE=Europe/Moscow
GOOGLE_CALENDAR_DEFAULT_EVENT_DURATION_MINUTES=60
GOOGLE_CALENDAR_SYNC_ON_READ=true
GOOGLE_CALENDAR_READ_MAX_RESULTS=20
```

Выбор голоса:

```bash
python -m voice.tts --list-voices
python -m voice.tts --voice Milena --text "Привет, это тест озвучки"
```

## Google Calendar

Настройка:
1. Создать Desktop App OAuth client в Google Cloud
2. Включить Google Calendar API
3. Сохранить credentials как `credentials.json` в корне проекта
4. Включить интеграцию через `.env`

Поведение:
- новые события могут отправляться в Google Calendar
- ближайшие события из Google Calendar могут импортироваться в SQLite
- если синхронизация с Google не удалась, Vasya продолжает работать локально и возвращает понятную ошибку

## Текущие ограничения

Это все еще MVP, поэтому ограничения пока такие:
- нет wake word
- нет режима постоянного прослушивания
- понимание речи все еще требует улучшения
- десктопный аватар пока это легкий первый виджет, а не полноценное desktop app
- пока нет menu bar приложения
- нет интеграции с Obsidian
- нет долговременной памяти
- нет специализированных code и writing agents

## Путь по версиям

- `v0.3.x`: базовый voice MVP, локальное хранилище, задачи и календарь, Google Calendar, hotkey режим
- `v0.4.0`: первый desktop widget MVP с assistant state layer и click-to-talk аватаром
- `v0.4.x`: упрощение установки, улучшение распознавания речи и desktop UX
- `v0.5.x`: более полноценный desktop shell с tray или menu bar app и richer avatar behavior
- `v0.6.x`: интеграция с Obsidian
- `v0.7.x`: code agent и writing/research agent

## Что запланировано

Ближайшие направления:
- улучшение понимания фраз и retry UX
- упрощение установки и первого запуска
- развитие desktop shell вокруг текущего widget MVP
- интеграция с Obsidian
- специализированные code и writing agents

Полный маршрут развития:
- см. [ROADMAP.md](ROADMAP.md)

## Безопасность

При использовании внешних интеграций важно отдельно учитывать:
- хранение токенов
- доступ к календарю
- доступ к файлам
- журналирование действий

## Заметки

На macOS для записи звука может понадобиться доступ Terminal или IDE к микрофону:
- `System Settings`
- `Privacy & Security`
- `Microphone`

Для глобальных горячих клавиш на macOS также может понадобиться:
- `System Settings`
- `Privacy & Security`
- `Accessibility`

Для desktop avatar widget также может понадобиться:
- `System Settings`
- `Privacy & Security`
- `Accessibility`

## Автор

Xelvhk

Личный проект по созданию локального голосового AI-ассистента, который со временем может вырасти в более широкую систему персонального AI.
