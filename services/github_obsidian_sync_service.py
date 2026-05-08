from __future__ import annotations

import re

from config.settings import (
    GITHUB_DEFAULT_REPO,
    OLLAMA_CHAT_NUM_PREDICT,
    OLLAMA_CHAT_TEMPERATURE,
    OLLAMA_CHAT_THINK,
)
from services.github_service import (
    GitHubServiceError,
    fetch_repository_metadata,
    fetch_repository_readme,
)
from services.integration_settings_service import get_integration_setting
from services.obsidian_service import upsert_obsidian_note, upsert_project_note_from_readme
from services.ollama_client import OllamaClientError, generate, resolve_chat_model

_PROJECT_TYPE_LABELS: dict[str, str] = {
    "web_saas": "Web/SaaS",
    "mobile_app": "Mobile app",
    "desktop_app": "Desktop app",
    "telegram_bot": "Telegram-бот",
    "voice_assistant": "Голосовой ассистент",
    "child_game": "Детские/игровые сценарии",
    "general": "Универсальный цифровой продукт",
}

_PROJECT_TYPE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "telegram_bot",
        ("telegram", "телеграм", "tg-бот", "бот", "bot"),
    ),
    (
        "voice_assistant",
        ("голос", "voice", "stt", "tts", "ассистент"),
    ),
    (
        "child_game",
        ("ребен", "дет", "игра", "считал", "слова"),
    ),
    (
        "mobile_app",
        ("ios", "android", "mobile", "смартфон", "приложение"),
    ),
    (
        "desktop_app",
        ("desktop", "windows", "mac", "linux", "qt", "electron"),
    ),
    (
        "web_saas",
        ("web", "saas", "браузер", "сайт", "лендинг", "crm"),
    ),
)


def update_obsidian_note(*, title: str, content: str, mode: str = "append") -> str:
    normalized_title = " ".join(str(title or "").strip().split())
    normalized_content = str(content or "").strip()
    if not normalized_content:
        return "Не указан текст для заметки в Obsidian."

    result = upsert_obsidian_note(
        title=normalized_title or "Vasya Note",
        content=normalized_content,
        mode="replace" if mode == "replace" else "append",
    )
    if not result.get("ok"):
        return str(result.get("error") or "Не удалось обновить заметку в Obsidian.")
    path = str(result.get("path", ""))
    if mode == "replace":
        return f"Готово. Обновила заметку в Obsidian: {path}."
    return f"Готово. Добавила в заметку Obsidian: {path}."


def sync_github_project_to_obsidian(*, repo: str | None = None) -> str:
    resolved_repo = _resolve_repo(repo)
    if not resolved_repo:
        return (
            "Не указан GitHub репозиторий. "
            "Скажи: добавь проект github owner/repo в обсидиан."
        )
    try:
        metadata = fetch_repository_metadata(resolved_repo)
        readme = fetch_repository_readme(resolved_repo)
    except GitHubServiceError as exc:
        return f"Не удалось получить данные проекта из GitHub: {exc}"
    except Exception as exc:
        return f"Ошибка при чтении GitHub: {type(exc).__name__}: {exc}"

    result = upsert_project_note_from_readme(
        repo=str(metadata.get("full_name") or resolved_repo),
        readme_markdown=str(readme.get("text") or ""),
        repo_description=str(metadata.get("description") or ""),
        repo_url=str(metadata.get("html_url") or ""),
        default_branch=str(metadata.get("default_branch") or "main"),
    )
    if not result.get("ok"):
        return str(result.get("error") or "Не удалось записать проект в Obsidian.")
    return (
        "Синхронизировала проект GitHub в Obsidian. "
        f"Файл: {result.get('path', '')}."
    )


def analyze_project_idea_to_obsidian(*, idea: str, title: str | None = None) -> str:
    normalized_idea = " ".join(str(idea or "").strip().split())
    if len(normalized_idea) < 25:
        return (
            "Идея пока слишком короткая для полезного плана. "
            "Опиши хотя бы цель, для кого проект и что должно работать в MVP."
        )

    project_type = _detect_project_type(normalized_idea)
    normalized_title = " ".join(str(title or "").strip().split()) or _derive_note_title(
        normalized_idea,
        project_type=project_type,
    )
    prompt = _build_project_plan_prompt(normalized_idea, project_type)
    try:
        markdown_plan = generate(
            prompt,
            model=resolve_chat_model(),
            think=OLLAMA_CHAT_THINK,
            temperature=min(0.35, max(0.05, OLLAMA_CHAT_TEMPERATURE)),
            num_predict=max(320, min(900, OLLAMA_CHAT_NUM_PREDICT * 4)),
        ).strip()
    except OllamaClientError as exc:
        return f"Не удалось проанализировать идею: {exc}"
    except Exception as exc:
        return f"Ошибка при анализе идеи: {type(exc).__name__}: {exc}"

    if not markdown_plan:
        return "Не получилось собрать план по идее. Попробуй чуть подробнее сформулировать идею."
    normalized_plan = _normalize_project_plan_markdown(markdown_plan, project_type=project_type)
    project_type_label = _PROJECT_TYPE_LABELS.get(project_type, _PROJECT_TYPE_LABELS["general"])

    content = (
        f"## Исходная идея\n\n{normalized_idea}\n\n"
        f"## Тип проекта\n\n{project_type_label}\n\n"
        f"## План реализации\n\n{normalized_plan}\n"
    )
    result = upsert_obsidian_note(
        title=normalized_title,
        content=content,
        mode="replace",
    )
    if not result.get("ok"):
        return str(result.get("error") or "Не удалось записать план идеи в Obsidian.")
    return (
        "Готово. Проанализировала идею и записала план в Obsidian: "
        f"{result.get('path', '')}."
    )


def _resolve_repo(repo: str | None) -> str:
    candidate = " ".join(str(repo or "").strip().split())
    if candidate:
        return candidate
    configured = get_integration_setting("github_default_repo")
    if configured:
        return configured
    return GITHUB_DEFAULT_REPO


def _derive_note_title(idea: str, *, project_type: str = "general") -> str:
    clean = re.sub(r"[^\w\s\-]+", " ", str(idea), flags=re.UNICODE)
    words = [part for part in clean.split() if part]
    short = " ".join(words[:8]).strip()
    if not short:
        short = "Новый проект"
    type_label = _PROJECT_TYPE_LABELS.get(project_type, _PROJECT_TYPE_LABELS["general"])
    compact = short[:56].strip()
    return f"Idea Plan • {type_label}: {compact}"


def _build_project_plan_prompt(idea: str, project_type: str) -> str:
    project_type_label = _PROJECT_TYPE_LABELS.get(project_type, _PROJECT_TYPE_LABELS["general"])
    focus_lines = _project_type_focus_lines(project_type)
    focus_block = "\n".join(f"- {item}" for item in focus_lines)
    return f"""
Ты продуктовый технический архитектор.
На основе идеи пользователя составь практичный план реализации проекта.

Формат ответа: Markdown на русском, без JSON.
Пиши структурно и конкретно, без воды.

Контекст проекта:
- Тип проекта: {project_type_label}
- Учитывай профиль типа проекта при формировании MVP и задач.

Фокус для этого типа:
{focus_block}

Обязательные разделы:
1. Цель и ценность (2-4 пункта)
2. MVP (что обязательно в первой версии)
3. Этапы реализации
4. Задачи по этапам (чек-лист)
5. Архитектурные решения
6. Риски и как снизить
7. Что сделать сегодня (первые 3 шага)

Требования к задачам:
- каждая задача начинается с "- [ ]"
- формулировки короткие и проверяемые
- если возможно, добавляй приоритет в скобках: (P0/P1/P2)

Идея:
{idea}
""".strip()


def _normalize_project_plan_markdown(markdown_plan: str, *, project_type: str = "general") -> str:
    text = str(markdown_plan or "").strip()
    if not text:
        return ""
    sections = _extract_markdown_sections(text)
    required_titles = (
        "Цель и ценность",
        "MVP",
        "Этапы реализации",
        "Задачи по этапам",
        "Архитектурные решения",
        "Риски и как снизить",
        "Что сделать сегодня",
    )
    if all(_lookup_section_content(sections, title) for title in required_titles):
        return text

    bullets = _extract_bullets(text)
    goals = bullets[:3] or ["Определить ценность проекта и целевую аудиторию."]
    mvp = bullets[3:6] or ["Собрать минимальный функциональный контур и проверить на первых пользователях."]
    phases = bullets[6:9] or _default_phases_for_project_type(project_type)
    tasks = bullets[9:17] or _default_tasks_for_project_type(project_type)
    architecture = _default_architecture_decisions_for_project_type(project_type)
    risks = bullets[17:20] or [
        "Риск расплывчатого scope — зафиксировать MVP-границы письменно.",
        "Риск затяжной реализации — идти итерациями и мерить прогресс по неделям.",
    ]
    first_steps = bullets[20:23] or [
        "Уточнить цель и аудиторию проекта в 3-5 пунктах.",
        "Собрать список обязательных MVP-функций.",
        "Разбить MVP на первые технические задачи.",
    ]

    return (
        f"### Цель и ценность\n{_as_bulleted(goals)}\n\n"
        f"### MVP\n{_as_bulleted(mvp)}\n\n"
        f"### Этапы реализации\n{_as_numbered(phases)}\n\n"
        f"### Задачи по этапам\n{_as_checklist(tasks)}\n\n"
        f"### Архитектурные решения\n{_as_bulleted(architecture)}\n\n"
        f"### Риски и как снизить\n{_as_bulleted(risks)}\n\n"
        f"### Что сделать сегодня\n{_as_numbered(first_steps)}"
    ).strip()


def _extract_markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_title = ""
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.+)$", line)
        if heading:
            current_title = heading.group(1).strip()
            sections.setdefault(current_title, [])
            continue
        if not current_title:
            continue
        sections[current_title].append(line)
    return {title: "\n".join(lines).strip() for title, lines in sections.items()}


def _lookup_section_content(sections: dict[str, str], title: str) -> str:
    target = title.lower().strip()
    for raw_title, content in sections.items():
        normalized = re.sub(r"\s+", " ", raw_title.lower()).strip()
        if target in normalized:
            return content
    return ""


def _extract_bullets(text: str) -> list[str]:
    result: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^[-*]\s+(.+)$", line)
        if not m:
            m = re.match(r"^\d+[.)]\s+(.+)$", line)
        if m:
            item = " ".join(m.group(1).strip().split())
            if item:
                result.append(item)
    if result:
        return result
    compact = " ".join(text.split())
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", compact) if part.strip()]
    return sentences[:12]


def _as_bulleted(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items if item.strip())


def _as_numbered(items: list[str]) -> str:
    rows: list[str] = []
    index = 1
    for item in items:
        if not item.strip():
            continue
        rows.append(f"{index}. {item}")
        index += 1
    return "\n".join(rows)


def _as_checklist(items: list[str]) -> str:
    return "\n".join(f"- [ ] {item}" for item in items if item.strip())


def _detect_project_type(idea: str) -> str:
    text = str(idea or "").lower()
    for project_type, hints in _PROJECT_TYPE_HINTS:
        if any(hint in text for hint in hints):
            return project_type
    return "general"


def _project_type_focus_lines(project_type: str) -> list[str]:
    focus_map: dict[str, list[str]] = {
        "web_saas": [
            "Учти регистрацию, onboarding и core-метрику активации.",
            "Добавь минимальный биллинг/тарифный контур, если это уместно.",
            "Предусмотри веб-аналитику и цикл обратной связи.",
        ],
        "mobile_app": [
            "Учти UX для маленьких экранов и офлайн/нестабильную сеть.",
            "Добавь push-уведомления только для ключевых сценариев.",
            "Сразу зафиксируй минимальный план релиза в Store/TestFlight.",
        ],
        "desktop_app": [
            "Покрой системный UX: автозапуск, трей/фон, горячие клавиши.",
            "Добавь план по кроссплатформенной упаковке и обновлениям.",
            "Пропиши безопасные системные интеграции и permissions.",
        ],
        "telegram_bot": [
            "Учти команды бота, fallback-кнопки и ограничения Telegram UI.",
            "Раздели сценарии первого касания и регулярного использования.",
            "Добавь план логирования и защиты от спама/повторов.",
        ],
        "voice_assistant": [
            "Оптимизируй time-to-first-response и баржа-ин (прерывание речи).",
            "Добавь fast-path для частых команд и подтверждений.",
            "Раздели голосовой и текстовый контуры взаимодействия.",
        ],
        "child_game": [
            "Сделай короткие циклы игры с быстрым откликом.",
            "Добавь безопасные и доброжелательные формулировки.",
            "Продумай простые правила входа/выхода из игровых режимов.",
        ],
        "general": [
            "Сфокусируйся на самом ценном пользовательском сценарии.",
            "Раздели MVP и backlog, чтобы быстрее дойти до первых пользователей.",
            "Добавь измеримые критерии успеха и короткие итерации.",
        ],
    }
    return focus_map.get(project_type, focus_map["general"])


def _default_tasks_for_project_type(project_type: str) -> list[str]:
    task_map: dict[str, list[str]] = {
        "web_saas": [
            "Сформулировать product scope, ICP и ключевую activation-метрику.",
            "Собрать базовый web-контур: auth, dashboard, ключевой сценарий.",
            "Подключить аналитику событий и метрики активации/удержания.",
            "Подготовить тарифы/ограничения и простую модель монетизации.",
        ],
        "mobile_app": [
            "Зафиксировать core user-flow для 2-3 основных экранов.",
            "Реализовать MVP-экраны с учетом офлайн/медленной сети.",
            "Добавить легкую телеметрию и трекинг критичных ошибок.",
            "Подготовить минимальный релизный чеклист для App Store/Google Play.",
        ],
        "desktop_app": [
            "Определить фоновый и активный режимы приложения на desktop.",
            "Реализовать системный UX: tray, hotkey, старт с системой.",
            "Подготовить упаковку и автообновление для целевых ОС.",
            "Добавить логирование системных действий и безопасные ограничения.",
        ],
        "telegram_bot": [
            "Согласовать набор команд и сценарий первого запуска бота.",
            "Реализовать обработку команд + кнопки для частых действий.",
            "Добавить устойчивую обработку ошибок и повторов webhook/polling.",
            "Подготовить FAQ и fallback-ответы для непонятых команд.",
        ],
        "voice_assistant": [
            "Оптимизировать голосовой контур: STT -> intent -> TTS с fast-path.",
            "Добавить короткие подтверждения и корректное прерывание озвучивания.",
            "Реализовать fallback на текст при неуверенном распознавании.",
            "Ввести UX-метрики: TTFR, TTA, доля нераспознаваний.",
        ],
        "child_game": [
            "Собрать 3-5 коротких игровых сценариев с понятными правилами.",
            "Добавить быстрые игровые команды: дальше, еще, подсказка, стоп.",
            "Сделать дружелюбные похвалы и безопасные ответы для детского режима.",
            "Проверить сценарии входа/выхода из игры без зависаний состояния.",
        ],
        "general": [
            "Сформулировать product scope и критерии успеха.",
            "Собрать технический каркас и базовую архитектуру.",
            "Реализовать ключевые пользовательские сценарии MVP.",
            "Добавить тесты и базовую диагностику.",
        ],
    }
    return task_map.get(project_type, task_map["general"])


def _default_phases_for_project_type(project_type: str) -> list[str]:
    phase_map: dict[str, list[str]] = {
        "web_saas": [
            "Этап 1: Product discovery и UX-поток онбординга.",
            "Этап 2: MVP ядро + интеграции/аналитика.",
            "Этап 3: Безопасность, релиз и цикл улучшений.",
        ],
        "mobile_app": [
            "Этап 1: UX-сценарии, прототип и архитектурный каркас.",
            "Этап 2: MVP функциональность + внешние интеграции.",
            "Этап 3: QA, безопасность, store-релиз и итерации.",
        ],
        "desktop_app": [
            "Этап 1: Каркас приложения и системный UX.",
            "Этап 2: MVP сценарии + OS/внешние интеграции.",
            "Этап 3: Безопасность, упаковка, обновления и релиз.",
        ],
        "telegram_bot": [
            "Этап 1: Сценарии диалога и команды бота.",
            "Этап 2: Реализация MVP + интеграции сервисов.",
            "Этап 3: Защита, наблюдаемость и прод-выкатка.",
        ],
        "voice_assistant": [
            "Этап 1: Голосовой контур и fast-path интентов.",
            "Этап 2: Интеграции инструментов и стабильность UX.",
            "Этап 3: Безопасность действий, метрики и релиз.",
        ],
        "child_game": [
            "Этап 1: Игровые сценарии и безопасный тон общения.",
            "Этап 2: Реализация игр + быстрые переходы между ними.",
            "Этап 3: Контроль качества, родительские ограничения и релиз.",
        ],
        "general": [
            "Этап 1: исследование и уточнение требований.",
            "Этап 2: реализация MVP и базовые тесты.",
            "Этап 3: интеграции, безопасность, релиз и стабилизация.",
        ],
    }
    return phase_map.get(project_type, phase_map["general"])


def _default_architecture_decisions_for_project_type(project_type: str) -> list[str]:
    architecture_map: dict[str, list[str]] = {
        "web_saas": [
            "Backend API: разделить публичные и внутренние endpoints, добавить RBAC для ролей.",
            "Хранилище: PostgreSQL для core-данных + отдельная таблица аудита критичных действий.",
            "Интеграции: Webhooks/queue для внешних сервисов, с retry и idempotency key.",
            "Безопасность: rate-limit + валидация входа + секреты только через env/secret store.",
        ],
        "mobile_app": [
            "Клиент: локальный кэш (SQLite/secure storage) для устойчивости офлайн-сценариев.",
            "API: versioned endpoints и единый контракт ошибок для мобильного клиента.",
            "Интеграции: push-канал только для приоритетных событий с контролем частоты.",
            "Безопасность: токены в secure enclave/keystore, PII не логировать в явном виде.",
        ],
        "desktop_app": [
            "Shell: отдельный слой UI и отдельный оркестратор действий/интентов.",
            "Хранилище: локальные данные в пользовательской папке с атомарной записью.",
            "Интеграции: OS tools через allowlist + подтверждение рискованных команд.",
            "Безопасность: журнал действий, ограничения на ввод/клики в чувствительных окнах.",
        ],
        "telegram_bot": [
            "Бот-контур: маршрутизация update types с дедупликацией по update_id.",
            "State: session/state store для многошаговых сценариев и подтверждений.",
            "Интеграции: внешние вызовы через таймауты, retries и fallback-ответы.",
            "Безопасность: allowlist админ-команд, защита от spam/flood.",
        ],
        "voice_assistant": [
            "Pipeline: streaming STT -> intent -> TTS с fast-path для частых команд.",
            "Router: отдельный слой intent routing + role-spec/prompt packs.",
            "Tools: explicit allowlist для OS/интеграций + confirm для рискованных действий.",
            "Observability: метрики TTFR/TTA, false barge-in и 'не расслышал'.",
        ],
        "child_game": [
            "State machine: явные игровые состояния и безопасный выход командой 'стоп'.",
            "Контент: шаблоны ответов с child-safe фильтрацией и без рискованных тем.",
            "Latency: partial/fast intents для 'дальше/еще/подсказка' без полного STT.",
            "Родительский контроль: отдельный профиль ограничений и лог игровых действий.",
        ],
        "general": [
            "Архитектура: разделить UI/оркестратор/сервисы и не смешивать уровни.",
            "Хранилище: единый слой доступа к данным + миграции схемы.",
            "Интеграции: каждый внешний API через адаптер и стабильный интерфейс.",
            "Безопасность: секреты в env, валидация входа, журнал критичных действий.",
        ],
    }
    return architecture_map.get(project_type, architecture_map["general"])
