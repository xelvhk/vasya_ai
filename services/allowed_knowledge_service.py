from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from urllib.parse import quote

from services.obsidian_service import resolve_obsidian_vault_path


ALLOWED_FOLDERS = ("10_Projects/Active", "30_Knowledge")
_MAX_NOTE_BYTES = 256_000
_WORDS = re.compile(r"(?u)\b[^\W_]{4,}\b")
_STOP_WORDS = {"какие", "какой", "какая", "проекта", "проектов", "документе", "документах", "about", "what", "where", "with", "from"}


@dataclass(frozen=True)
class KnowledgeHit:
    relative_path: str
    title: str
    excerpt: str
    url: str
    modified_at: datetime


@dataclass(frozen=True)
class KnowledgeSearchResult:
    hits: tuple[KnowledgeHit, ...]
    error: str | None = None
    stale: bool = False
    observed_at: datetime | None = None


@dataclass(frozen=True)
class AllowedNote:
    relative_path: str
    title: str
    content: str
    modified_at: datetime


def resolve_knowledge_vault_path() -> Path:
    explicit = os.getenv("VASYA_KNOWLEDGE_VAULT_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    configured, _error = resolve_obsidian_vault_path()
    if configured is not None:
        return configured
    return Path.home() / "Documents" / "Obsidian Vault"


def search_allowed_notes(
    query: str, *, vault_path: Path | None = None, limit: int = 3
) -> KnowledgeSearchResult:
    vault = (vault_path or resolve_knowledge_vault_path()).expanduser()
    notes, error = collect_allowed_notes(vault)
    if error:
        return KnowledgeSearchResult((), error)
    return KnowledgeSearchResult(rank_allowed_notes(query, notes, vault=vault, limit=limit))


def collect_allowed_notes(vault: Path) -> tuple[tuple[AllowedNote, ...], str | None]:
    if not vault.is_dir():
        return (), "Obsidian vault недоступен."

    vault_real = vault.resolve()
    notes: list[AllowedNote] = []
    found_folder = False
    for folder_name in ALLOWED_FOLDERS:
        folder = vault / folder_name
        if folder.is_symlink() or not folder.is_dir():
            continue
        folder_real = folder.resolve()
        if not folder_real.is_relative_to(vault_real):
            continue
        found_folder = True
        for path in folder.rglob("*.md"):
            if path.is_symlink() or not path.is_file():
                continue
            if not path.resolve().is_relative_to(folder_real):
                continue
            try:
                stat = path.stat()
                if stat.st_size > _MAX_NOTE_BYTES:
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return (), "Не удалось прочитать разрешённую заметку."
            notes.append(
                AllowedNote(
                    relative_path=path.relative_to(vault).as_posix(),
                    title=path.stem,
                    content=content,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                )
            )

    if not found_folder:
        return (), "Разрешённые папки Obsidian недоступны."
    return tuple(notes), None


def rank_allowed_notes(
    query: str, notes: tuple[AllowedNote, ...], *, vault: Path, limit: int = 3
) -> tuple[KnowledgeHit, ...]:
    terms = tuple(
        word for word in _WORDS.findall(query.casefold()) if word not in _STOP_WORDS
    )
    if not terms:
        return ()
    ranked: list[tuple[int, KnowledgeHit]] = []
    for note in notes:
        lowered = note.content.casefold()
        title_lower = note.title.casefold()
        matched = [term for term in terms if term in title_lower or term in lowered]
        if not matched:
            continue
        score = sum(3 * (term in title_lower) + (term in lowered) for term in matched)
        url = (
            "obsidian://open?vault="
            f"{quote(vault.name, safe='')}&file={quote(note.relative_path, safe='')}"
        )
        ranked.append(
            (
                score,
                KnowledgeHit(
                    relative_path=note.relative_path,
                    title=note.title,
                    excerpt=_best_excerpt(note.content, matched),
                    url=url,
                    modified_at=note.modified_at,
                ),
            )
        )
    ranked.sort(key=lambda item: (-item[0], item[1].relative_path))
    return tuple(hit for _score, hit in ranked[: max(1, min(limit, 5))])


def _best_excerpt(content: str, terms: tuple[str, ...] | list[str]) -> str:
    lines = [" ".join(line.split()) for line in content.splitlines()]
    candidates = [line for line in lines if line and line != "---" and not line.startswith("#")]
    if not candidates:
        return ""
    best = max(candidates, key=lambda line: sum(term in line.casefold() for term in terms))
    return best[:300].rstrip()
