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

    normalized_title = " ".join(str(title or "").strip().split()) or _derive_note_title(normalized_idea)
    prompt = _build_project_plan_prompt(normalized_idea)
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
    normalized_plan = _normalize_project_plan_markdown(markdown_plan)

    content = (
        f"## Исходная идея\n\n{normalized_idea}\n\n"
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


def _derive_note_title(idea: str) -> str:
    clean = re.sub(r"[^\w\s\-]+", " ", str(idea), flags=re.UNICODE)
    words = [part for part in clean.split() if part]
    short = " ".join(words[:8]).strip()
    if not short:
        return "Project Idea Plan"
    return f"Project Idea - {short[:72].strip()}"


def _build_project_plan_prompt(idea: str) -> str:
    return f"""
Ты продуктовый технический архитектор.
На основе идеи пользователя составь практичный план реализации проекта.

Формат ответа: Markdown на русском, без JSON.
Пиши структурно и конкретно, без воды.

Обязательные разделы:
1. Цель и ценность (2-4 пункта)
2. MVP (что обязательно в первой версии)
3. Этапы реализации
4. Задачи по этапам (чек-лист)
5. Риски и как снизить
6. Что сделать сегодня (первые 3 шага)

Требования к задачам:
- каждая задача начинается с "- [ ]"
- формулировки короткие и проверяемые
- если возможно, добавляй приоритет в скобках: (P0/P1/P2)

Идея:
{idea}
""".strip()


def _normalize_project_plan_markdown(markdown_plan: str) -> str:
    text = str(markdown_plan or "").strip()
    if not text:
        return ""
    sections = _extract_markdown_sections(text)
    required_titles = (
        "Цель и ценность",
        "MVP",
        "Этапы реализации",
        "Задачи по этапам",
        "Риски и как снизить",
        "Что сделать сегодня",
    )
    if all(_lookup_section_content(sections, title) for title in required_titles):
        return text

    bullets = _extract_bullets(text)
    goals = bullets[:3] or ["Определить ценность проекта и целевую аудиторию."]
    mvp = bullets[3:6] or ["Собрать минимальный функциональный контур и проверить на первых пользователях."]
    phases = bullets[6:9] or [
        "Этап 1: исследование и уточнение требований.",
        "Этап 2: реализация MVP и базовые тесты.",
        "Этап 3: итерация по обратной связи и стабилизация.",
    ]
    tasks = bullets[9:17] or [
        "Сформулировать product scope и критерии успеха.",
        "Собрать технический каркас и базовую архитектуру.",
        "Реализовать ключевые пользовательские сценарии MVP.",
        "Добавить тесты и базовую диагностику.",
    ]
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
