# Vasya AI

Локальный голосовой ассистент и центр управления проектами для рабочего стола.

Vasya объединяет desktop-компаньона на PySide и **Vasya Project OS** — локальный
веб-дашборд проектов, задач, статусов и контекста. Основные данные остаются на
компьютере пользователя, а внешние сервисы подключаются только при необходимости.

**Текущий опубликованный тег:** `v0.6.0`

**Текущий трек разработки:** тестовая macOS-сборка `v0.7.0`

**Язык:** [English](README.md) | Русский

## Как выглядит продукт

### Vasya Project OS

![Пустой дашборд Vasya Project OS в новом профиле](docs/screenshots/project-os-dashboard.png)

Новая установка начинает работу с пустого реестра. В поставку не входят проекты
разработчика, персональные пути или локальные данные.

### Desktop-ассистент

![Настройки desktop-ассистента Vasya с превью аватара](docs/screenshots/desktop-settings.png)

Desktop-оболочка отвечает за аватар, меню в трее, глобальные горячие клавиши,
голосовую активацию, диктовку и локальные настройки.

## Что работает сейчас

- Голосовые и текстовые команды для задач, событий, заметок и диалога.
- Локальное распознавание речи, маршрутизация и чат через Ollama, настраиваемый TTS.
- Состояния аватара, меню в трее, горячие клавиши, ответы-подсказки и настройки.
- Morning Brief и поиск по локальному Memory Center.
- Vasya Project OS с пользовательским реестром проектов, Git-статусом и сводкой
  следующих действий.
- Версионируемый backup с предпросмотром и восстановлением без тихой перезаписи
  более новых данных.
- Опциональные интеграции с Google Calendar, Notion, GitHub и Obsidian.
- Локальный FastAPI для чата, задач, событий, заметок, памяти и Project OS.
- Контракт read-only коннекторов и базовая проверка доступности EventKit на macOS.

## Текущие границы

Следующие возможности запланированы или ещё не завершены:

- Подписанного и нотарифицированного DMG пока нет. Текущая macOS-сборка — это
  неподписанный ZIP для тестирования.
- Интеграция Eva через Apple Reminders и Calendar пока не читает записи. Осталось
  реализовать разрешения, выбор источников, нормализацию и синхронизацию.
- Голосовое создание задач во внешних системах, commit и push не включены.
  Изменяющие действия агента будут проходить через очередь подтверждений.
- Установщиков для Windows и Linux пока нет.

Текущий шаг и его критерии готовности находятся в
[последовательном плане выполнения](docs/EXECUTION_PLAN.md).

## Быстрый запуск на macOS

Понадобятся Python 3.11+, [Ollama](https://ollama.com/) и рабочий микрофон.

```bash
git clone https://github.com/xelvhk/vasya_ai.git
cd vasya_ai
bash scripts/setup_mac.sh
source .venv/bin/activate
ollama pull llama3
python scripts/doctor.py
python main.py
```

Ручная настройка окружения:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/doctor.py
python main.py
```

Поддерживаемая инструкция первого запуска:
[docs/FIRST_RUN.md](docs/FIRST_RUN.md).

## Запуск Project OS

Запустите локальный API:

```bash
source .venv/bin/activate
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8787 --reload
```

Откройте [http://127.0.0.1:8787/control-center](http://127.0.0.1:8787/control-center).
Защита API включена по умолчанию. В кнопке **Подключение** укажите
`VASYA_API_AUTH_TOKEN` из локального файла `.env`.

## Голосовая диктовка

Vasya может отправлять распознанный текст в активное поле ОС или на разрешённый
HTTP endpoint. Выбор находится в **Настройки > Интеграции > Режим диктовки**.
В API-режиме отправляется:

```json
{"text": "Распознанный текст", "source": "vasya_dictation_mode"}
```

Настроенный токен передаётся как Bearer token. Хост ограничивается переменной
`DICTATION_API_ALLOWED_HOSTS`, которая по умолчанию разрешает только localhost.

## Данные и приватность

- Основные записи хранятся в SQLite и локальных файлах в системном каталоге
  данных приложения.
- Новый профиль не содержит проектов или путей разработчика.
- Секреты интеграций по возможности хранятся в системном keyring и не попадают
  в backup.
- Кэши моделей и крупные сгенерированные файлы также исключены из backup.
- Внешние интеграции работают только после настройки пользователем.

Схема каталогов, миграция и состав backup описаны в
[docs/APP_DATA.md](docs/APP_DATA.md).

## Архитектура

```text
Desktop UI                 Project OS
scripts/avatar_widget.py   apps/control_center/*
          \                  /
           apps/api/* (FastAPI)
                    |
       оркестрация и маршрутизация
                    |
             предметные агенты
                    |
          сервисы и репозитории
                    |
 локальные данные + внешние коннекторы
```

Основной стек:

- Python 3.11+ и PySide6
- FastAPI
- Ollama
- faster-whisper
- SQLite
- sounddevice и scipy

## Тестовая macOS-сборка

Репозиторий умеет собирать локальное неподписанное `.app` и ZIP с
`Vasya AI.app` и `Vasya AI Doctor`:

```bash
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python scripts/build_macos_app.py
.venv/bin/python scripts/smoke_macos_app.py
.venv/bin/python scripts/build_macos_doctor.py
.venv/bin/python scripts/package_macos_app.py
.venv/bin/python scripts/smoke_macos_zip.py
.venv/bin/python scripts/smoke_macos_unpacked_zip.py
```

Это тестовый артефакт, а не публичный подписанный релиз. Подробности:
[docs/PACKAGING_PROTOTYPE.md](docs/PACKAGING_PROTOTYPE.md) и
[docs/PACKAGING_PLAN.md](docs/PACKAGING_PLAN.md).

## Конфигурация и безопасность

Скопируйте `.env.example` в `.env` и настройте только нужные локальные
параметры и интеграции.

Основные группы:

- LLM и голос: `OLLAMA_*`, `WHISPER_*`, `VOICE_*`, `TTS_*`
- Desktop UI: `HOTKEY_*`, `AVATAR_*`
- Интеграции: `GOOGLE_CALENDAR_*`, `NOTION_*`, `GITHUB_*`
- API: `VASYA_API_AUTH_TOKEN`, `VASYA_API_REQUIRE_AUTH`,
  `VASYA_API_ALLOW_QUERY_TOKEN`

Локальный API по умолчанию требует авторизацию для `/v1/*` и ограничивает
частоту запросов к чату, pipeline и голосовому WebSocket.

## Карта документации

- [План выполнения](docs/EXECUTION_PLAN.md): единая последовательная очередь работ.
- [План Project OS](docs/PROJECT_OS_PLAN.md): архитектура дашборда и коннекторов.
- [План упаковки](docs/PACKAGING_PLAN.md): этапы установщиков и публичного релиза.
- [Данные приложения](docs/APP_DATA.md): локальное хранение и миграция.
- [Release notes](docs/RELEASE_NOTES.md): изменения текущего релизного трека.
- [UI design system](docs/UI_DESIGN_SYSTEM.md): общие правила desktop- и web-интерфейсов.
- [Безопасность](docs/SECURITY_ISSUES.md): известные вопросы и меры защиты.
- [Продуктовый roadmap](ROADMAP.md): долгосрочное направление.

## Проверка

```bash
COSYVOICE_PYTHON= .venv/bin/python -m unittest discover tests
.venv/bin/python -m compileall agents apps assistant config core interfaces repositories scripts services tests utils voice main.py
git diff --check
```

CI выполняет проверку синтаксиса, полный набор unit-тестов и строгий smoke-тест
первого запуска через doctor.

## Ответственное использование

Vasya — ассистент для продуктивности, а не медицинская, юридическая или
экстренная система. Проверяйте важные распознанные команды, особенно если они
могут повлиять на другие приложения или внешние сервисы.

## Лицензия

GNU AGPLv3. См. [LICENSE](LICENSE).
