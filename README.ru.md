# Vasya AI

`VAS = Voice AI Assistant`

Язык: [English](README.md) | **Русский**

Локальный voice-first AI-ассистент с текущим MVP-фокусом на macOS и дальнейшим развитием в сторону Windows и Linux.
Vasya развивается из CLI MVP в более широкую систему персонального AI: задачи, календарь, будущие сценарии для заметок, десктопный интерфейс и специализированные агенты.

Текущая версия: `0.4.2`

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
- управляться через tray или menu bar style control
- поддерживать более живой разговорный UX с follow-up и более быстрым chat path
- запускать детские голосовые игры через отдельный игровой агент

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
- работать в desktop background и запускать голосовой цикл по горячей клавише
- показывать виджет-аватар с click-to-talk и индикацией состояний
- управляться через tray-иконку
- показывать более живые промежуточные статусы во время ответа
- удалять все задачи с голосовым подтверждением
- играть с ребенком в слова, прятки, загадки, угадай животное и повтори за мной

Примеры команд:
- `Добавь задачу купить лампу`
- `Какие у меня задачи?`
- `Добавь встречу с Сашей завтра в 18:00`
- `Покажи события на 30 марта`
- `Замолчи`
- `Выход`

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

Desktop shell:

```bash
python main.py
```

Headless фоновый режим с горячей клавишей:

```bash
python scripts/hotkey_daemon.py
```

Desktop avatar widget MVP:

```bash
python scripts/avatar_widget.py
```

Что умеет:
- `python main.py` теперь запускает desktop shell
- левый клик запускает один голосовой цикл
- глобальная горячая клавиша тоже работает внутри процесса виджета
- перетаскивание двигает аватар по экрану
- клик по tray-иконке скрывает или показывает аватар
- автозапуск при входе в macOS можно включить из меню Васи или командой `python scripts/autostart_macos.py install`
- через tray-меню можно запустить listening или завершить Vasya
- через tray и меню аватара доступны настройки размера, позиции, hotkey и tray-click behavior
- по умолчанию Vasya использует встроенный процедурный живой аватар
- через `AVATAR_IMAGE_PATH` можно подставить свой PNG или SVG-аватар, если захочешь переопределить внешний вид
- позиция виджета сохраняется между запусками
- рядом с аватаром показывается bubble во время listening, thinking, speaking и error
- правый клик открывает контекстное меню аватара

Текущий платформенный фокус:
- рабочий MVP сейчас ориентирован на macOS
- в дальнейшем планируется поддержка Windows и Linux

## Конфигурация

Основные настройки находятся в `config/settings.py`.

Пример:

```env
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3
OLLAMA_FAST_MODEL=llama3
OLLAMA_REASONING_MODEL=llama3
OLLAMA_FAST_THINK=false
OLLAMA_FAST_TEMPERATURE=0.1
OLLAMA_FAST_NUM_PREDICT=256
AUDIO_FILENAME=input.wav
RECORD_SECONDS=5
WHISPER_MODEL=base

TTS_VOICE=Milena
TTS_RATE=185
TTS_BACKEND=auto
TTS_PROFILE=ruslan_direct
PIPER_COMMAND=piper
PIPER_MODEL_PATH=storage/voices/ru_RU-ruslan-medium.onnx
PIPER_SPEAKER=
PIPER_LENGTH_SCALE=1.0
TTS_STATE_FILE=storage/tts_settings.json
VOICE_INPUT_BACKEND=auto
HOTKEY_COMBINATION=<cmd>+<option>+<space>
HOTKEY_EXIT_COMBINATION=<cmd>+<option>+q
AVATAR_IMAGE_PATH=
AVATAR_SIZE=210
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

Для более быстрого intent parsing:
- `OLLAMA_FAST_MODEL` используется для коротких команд
- `OLLAMA_FAST_THINK=false` отключает reasoning на fast-path
- `OLLAMA_FAST_NUM_PREDICT` стоит держать небольшим, например `128` или `256`

Выбор голоса:

```bash
python -m voice.tts --list-profiles
python -m voice.tts --list-voices
python -m voice.tts --profile ruslan_direct --text "Привет, это тест озвучки"
```

Профили голоса:
- `ruslan_direct` — мужской, быстрый и прямой

Системные голосовые команды:
- `Замолчи`
- `Останови озвучивание`
- `Выход`
- `Закройся`

Альтернативный путь для TTS:
- `say` пока остается самым простым встроенным вариантом для macOS
- `auto` теперь сам выберет `piper`, если команда установлена и настроен `PIPER_MODEL_PATH`
- `piper` можно принудительно включить через `TTS_BACKEND=piper`
- для `piper` нужно как минимум указать `PIPER_MODEL_PATH`
- при первой озвучке Vasya печатает, какой TTS backend реально используется
- для русской локальной озвучки можно скачать текущий голос так: `python scripts/setup_piper_ru.py --voices ruslan`

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
- `v0.4.1`: улучшенный conversational UX, voice confirmations, faster chat path, safer bulk task deletion
- `v0.4.2`: детский игровой режим и игровой агент
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
