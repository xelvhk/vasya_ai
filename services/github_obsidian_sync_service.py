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

    content = (
        f"## Исходная идея\n\n{normalized_idea}\n\n"
        f"## План реализации\n\n{markdown_plan}\n"
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
