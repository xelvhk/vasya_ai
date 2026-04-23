from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from config.settings import (
    OBSIDIAN_EDIT_NOTES_DIR,
    OBSIDIAN_EXPORT_NOTES_DIR,
    OBSIDIAN_PROJECTS_DIR,
    OBSIDIAN_VAULT_PATH,
)


def export_notes_to_obsidian(notes: list[dict]) -> dict:
    vault_path, error = _resolve_vault_path()
    if error:
        return {
            "ok": False,
            "error": error,
        }

    export_dir = vault_path / OBSIDIAN_EXPORT_NOTES_DIR
    export_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    export_path = export_dir / f"Vasya Notes {timestamp}.md"
    export_path.write_text(_build_notes_markdown(notes), encoding="utf-8")
    return {
        "ok": True,
        "path": str(export_path),
        "count": len(notes),
    }


def upsert_obsidian_note(
    *,
    title: str,
    content: str,
    mode: str = "append",
) -> dict:
    normalized_title = _normalize_note_title(title)
    normalized_content = str(content or "").strip()
    if not normalized_content:
        return {"ok": False, "error": "Не указан текст для заметки Obsidian."}

    vault_path, error = _resolve_vault_path()
    if error:
        return {"ok": False, "error": error}

    target_dir = vault_path / (OBSIDIAN_EDIT_NOTES_DIR or OBSIDIAN_EXPORT_NOTES_DIR or "Vasya Inbox")
    target_dir.mkdir(parents=True, exist_ok=True)
    note_path = target_dir / f"{_safe_filename(normalized_title)}.md"
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if mode == "replace":
        payload = (
            f"# {normalized_title}\n\n"
            f"_Updated: {now_text}_\n\n"
            f"{normalized_content}\n"
        )
        note_path.write_text(payload, encoding="utf-8")
    else:
        existing = ""
        if note_path.exists():
            existing = note_path.read_text(encoding="utf-8").strip()
        append_block = f"## {now_text}\n\n{normalized_content}\n"
        if not existing:
            payload = f"# {normalized_title}\n\n{append_block}"
        else:
            payload = f"{existing}\n\n{append_block}"
        note_path.write_text(payload, encoding="utf-8")

    return {"ok": True, "path": str(note_path), "title": normalized_title, "mode": mode}


def upsert_project_note_from_readme(
    *,
    repo: str,
    readme_markdown: str,
    repo_description: str = "",
    repo_url: str = "",
    default_branch: str = "",
) -> dict:
    normalized_repo = " ".join(str(repo).strip().split())
    if not normalized_repo or "/" not in normalized_repo:
        return {"ok": False, "error": "Нужен GitHub репозиторий в формате owner/repo."}

    vault_path, error = _resolve_vault_path()
    if error:
        return {"ok": False, "error": error}

    projects_dir = vault_path / (OBSIDIAN_PROJECTS_DIR or "Projects")
    projects_dir.mkdir(parents=True, exist_ok=True)

    owner, name = normalized_repo.split("/", maxsplit=1)
    note_title = f"Project {owner}/{name}"
    note_path = projects_dir / f"{_safe_filename(owner)}-{_safe_filename(name)}.md"
    body = _build_project_note(
        repo=normalized_repo,
        readme_markdown=readme_markdown,
        repo_description=repo_description,
        repo_url=repo_url,
        default_branch=default_branch,
    )
    note_path.write_text(body, encoding="utf-8")
    return {"ok": True, "path": str(note_path), "title": note_title}


def _build_notes_markdown(notes: list[dict]) -> str:
    lines = [
        "# Vasya Notes Export",
        "",
        f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    if not notes:
        lines.append("_No notes yet._")
        lines.append("")
        return "\n".join(lines)

    for note in notes:
        created_at = note.get("created_at") or ""
        content = str(note.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"## {created_at or 'Without date'}")
        lines.append("")
        lines.append(content)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _resolve_vault_path() -> tuple[Path | None, str | None]:
    vault_path = Path(OBSIDIAN_VAULT_PATH).expanduser() if OBSIDIAN_VAULT_PATH else None
    if vault_path is None or not str(vault_path).strip():
        return None, "Путь к Obsidian vault не настроен. Добавь OBSIDIAN_VAULT_PATH в .env."
    if not vault_path.exists() or not vault_path.is_dir():
        return None, "Путь к Obsidian vault не найден. Проверь OBSIDIAN_VAULT_PATH."
    return vault_path, None


def _normalize_note_title(title: str) -> str:
    cleaned = " ".join(str(title or "").strip().split())
    return cleaned if cleaned else "Vasya Note"


def _safe_filename(value: str) -> str:
    base = re.sub(r"[^\w\-. ]+", " ", str(value), flags=re.UNICODE).strip()
    base = re.sub(r"\s+", "_", base)
    return base[:120] or "note"


def _build_project_note(
    *,
    repo: str,
    readme_markdown: str,
    repo_description: str,
    repo_url: str,
    default_branch: str,
) -> str:
    summary = _extract_readme_summary(readme_markdown)
    setup_section = _extract_section_block(readme_markdown, ("install", "setup", "quick start", "usage", "запуск"))
    tasks = _extract_tasks(readme_markdown)
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    description = " ".join(str(repo_description).strip().split())

    lines = [
        f"# Project {repo}",
        "",
        f"_Updated: {updated_at}_",
        "",
        "## Описание",
        "",
        description or summary or "Описание пока не найдено в README.",
        "",
    ]

    if repo_url:
        lines.extend(
            [
                "## Ссылки",
                "",
                f"- Repo: {repo_url}",
                f"- README: {repo_url}/blob/{default_branch or 'main'}/README.md",
                "",
            ]
        )

    if summary:
        lines.extend(
            [
                "## Коротко о проекте",
                "",
                summary,
                "",
            ]
        )

    if setup_section:
        lines.extend(
            [
                "## Быстрый старт (из README)",
                "",
                setup_section,
                "",
            ]
        )

    lines.extend(
        [
            "## Задачи",
            "",
        ]
    )
    if tasks:
        for task in tasks[:14]:
            lines.append(f"- [ ] {task}")
    else:
        lines.extend(
            [
                "- [ ] Уточнить ключевые цели проекта",
                "- [ ] Сверить roadmap и ближайший спринт",
                "- [ ] Зафиксировать приоритеты по улучшениям",
            ]
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def _extract_readme_summary(readme_markdown: str) -> str:
    for raw in str(readme_markdown or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("#", "-", "*", ">")):
            continue
        if line.startswith("```"):
            continue
        if len(line) < 30:
            continue
        return line[:420]
    return ""


def _extract_section_block(readme_markdown: str, keywords: tuple[str, ...]) -> str:
    sections: dict[str, list[str]] = {}
    current = ""
    for raw in str(readme_markdown or "").splitlines():
        line = raw.rstrip()
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.*)$", line)
        if heading:
            current = heading.group(1).strip().lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections.setdefault(current, []).append(line)

    for title, content in sections.items():
        if not any(keyword in title for keyword in keywords):
            continue
        cleaned = [line for line in content if line.strip()][:16]
        if not cleaned:
            continue
        return "\n".join(cleaned).strip()
    return ""


def _extract_tasks(readme_markdown: str) -> list[str]:
    tasks: list[str] = []
    seen: set[str] = set()
    for raw in str(readme_markdown or "").splitlines():
        line = raw.strip()
        checkbox = re.match(r"^[-*]\s+\[[ xX]\]\s+(.+)$", line)
        if checkbox:
            task = checkbox.group(1).strip()
        elif "todo" in line.lower() or "to-do" in line.lower():
            task = re.sub(r"^[-*]\s*", "", line, flags=re.IGNORECASE).strip()
        else:
            continue
        normalized = " ".join(task.split())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        tasks.append(normalized)
    return tasks
