from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import re

from config.settings import OBSIDIAN_DAILY_NOTES_DIR, OBSIDIAN_DAILY_NOTES_DIRS
from services.obsidian_service import resolve_obsidian_vault_path

_CHECKBOX_RE = re.compile(r"^(\s*[-*]\s+\[)([ xX])(\]\s+)(.+)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class DailyTaskItem:
    id: str
    task: str
    completed: bool
    datetime: str | None
    note_path: str
    line_index: int
    date: str
    section: str

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "task": self.task,
            "completed": self.completed,
            "datetime": self.datetime,
            "note_path": self.note_path,
            "line_index": self.line_index,
            "date": self.date,
            "section": self.section,
        }


def create_task_in_daily_note(task: str, dt: str | None = None) -> dict:
    date_key = _date_from_dt(dt)
    path = _daily_note_path(date_key)
    if path is None:
        return {"task": task.strip(), "datetime": dt}
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines()
    insert_index = _find_tasks_insert_index(lines)
    entry = f"- [ ] {task.strip()}"
    if insert_index is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("## Задачи")
        lines.append("")
        lines.append(entry)
    else:
        lines.insert(insert_index, entry)
    payload = "\n".join(lines).rstrip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return {"task": task.strip(), "datetime": dt, "note_path": str(path), "source": "obsidian_daily"}


def list_tasks_from_daily_notes(filter_date: str | None = None) -> list[dict]:
    if filter_date and "недел" in filter_date.lower():
        return [item.as_dict() for item in _read_week_tasks(_today_date()) if not item.completed]

    date_key = _date_from_dt(filter_date)
    return [item.as_dict() for item in _read_note_tasks(date_key) if not item.completed]


def complete_task_in_daily_notes(*, target: str, filter_date: str | None = None) -> dict | None:
    resolved = _resolve_task_target(target=target, filter_date=filter_date)
    if resolved is None:
        return None
    lines = Path(resolved.note_path).read_text(encoding="utf-8").splitlines()
    line = lines[resolved.line_index]
    match = _CHECKBOX_RE.match(line)
    if not match:
        return None
    lines[resolved.line_index] = f"{match.group(1)}x{match.group(3)}{match.group(4)}"
    Path(resolved.note_path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return resolved.as_dict()


def delete_task_from_daily_notes(*, target: str, filter_date: str | None = None) -> bool:
    resolved = _resolve_task_target(target=target, filter_date=filter_date)
    if resolved is None:
        return False
    path = Path(resolved.note_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    if resolved.line_index < 0 or resolved.line_index >= len(lines):
        return False
    lines.pop(resolved.line_index)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def delete_all_open_tasks_in_daily_notes(*, filter_date: str | None = None) -> int:
    if filter_date and "недел" in filter_date.lower():
        days = _week_dates(_today_date())
    else:
        days = [_date_from_dt(filter_date)]
    deleted = 0
    for date_key in days:
        path = _daily_note_path(date_key)
        if path is None or not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        kept: list[str] = []
        for line in lines:
            match = _CHECKBOX_RE.match(line)
            if match and match.group(2).lower() == " ":
                deleted += 1
                continue
            kept.append(line)
        path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    return deleted


def count_open_tasks_in_daily_notes(*, filter_date: str | None = None) -> int:
    return len(list_tasks_from_daily_notes(filter_date=filter_date))


def _resolve_task_target(*, target: str, filter_date: str | None = None) -> DailyTaskItem | None:
    items = [DailyTaskItem(**item) for item in list_tasks_from_daily_notes(filter_date=filter_date)]
    normalized = str(target or "").strip()
    if not normalized:
        return None
    for item in items:
        if item.id == normalized:
            return item
    if normalized.isdigit():
        index = int(normalized) - 1
        if 0 <= index < len(items):
            return items[index]
        return None
    lowered = normalized.casefold()
    for item in items:
        if item.task.casefold() == lowered:
            return item
    for item in items:
        if lowered in item.task.casefold():
            return item
    return None


def _read_week_tasks(anchor_date: str) -> list[DailyTaskItem]:
    tasks: list[DailyTaskItem] = []
    for date_key in _week_dates(anchor_date):
        tasks.extend(_read_note_tasks(date_key))
    return tasks


def _read_note_tasks(date_key: str) -> list[DailyTaskItem]:
    path = _daily_note_path(date_key)
    if path is None or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    result: list[DailyTaskItem] = []
    current_section = ""
    for idx, line in enumerate(lines):
        heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.+)$", line.strip())
        if heading_match:
            current_section = _normalize_section_name(heading_match.group(1))
            continue
        match = _CHECKBOX_RE.match(line)
        if not match:
            continue
        completed = match.group(2).lower() == "x"
        task_text = " ".join(match.group(4).strip().split())
        if not task_text:
            continue
        task_id = f"{date_key}:{idx + 1}"
        result.append(
            DailyTaskItem(
                id=task_id,
                task=task_text,
                completed=completed,
                datetime=date_key,
                note_path=str(path),
                line_index=idx,
                date=date_key,
                section=current_section,
            )
        )
    return sorted(
        result,
        key=lambda item: (_section_priority(item.section), item.line_index),
    )


def _normalize_section_name(raw: str) -> str:
    return " ".join(str(raw or "").strip().lower().split())


def _section_priority(section: str) -> int:
    normalized = _normalize_section_name(section)
    if normalized in {"план на день", "day plan", "daily plan"}:
        return 0
    if normalized in {"план недели", "план на неделю", "week plan", "weekly plan"}:
        return 1
    if normalized in {"задачи", "tasks", "todo", "to-do"}:
        return 2
    return 3


def _find_tasks_insert_index(lines: list[str]) -> int | None:
    for idx, raw in enumerate(lines):
        heading = raw.strip().lower()
        if heading in {"## задачи", "# задачи", "## tasks", "# tasks"}:
            insert_idx = idx + 1
            while insert_idx < len(lines):
                line = lines[insert_idx]
                stripped = line.strip()
                if not stripped:
                    insert_idx += 1
                    continue
                if stripped.startswith("#"):
                    return insert_idx
                if _CHECKBOX_RE.match(line):
                    insert_idx += 1
                    continue
                return insert_idx
            return len(lines)
    return None


def _daily_note_path(date_key: str) -> Path | None:
    vault_path, _error = resolve_obsidian_vault_path()
    if vault_path is None:
        return None
    daily_dir = _resolve_daily_notes_dir(vault_path)
    return daily_dir / f"{date_key}.md"


def _resolve_daily_notes_dir(vault_path: Path) -> Path:
    candidates: list[str] = []
    for item in OBSIDIAN_DAILY_NOTES_DIRS:
        normalized = str(item or "").strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    legacy = str(OBSIDIAN_DAILY_NOTES_DIR or "").strip()
    if legacy and legacy not in candidates:
        candidates.append(legacy)
    if not candidates:
        candidates = ["Daily", "Ежедневные"]

    for dirname in candidates:
        path = vault_path / dirname
        if path.exists() and path.is_dir():
            return path
    return vault_path / candidates[0]


def _date_from_dt(raw_dt: str | None) -> str:
    text = str(raw_dt or "").strip()
    if _DATE_RE.match(text):
        return text
    if len(text) >= 10 and _DATE_RE.match(text[:10]):
        return text[:10]
    return _today_date()


def _today_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _week_dates(anchor_date: str) -> list[str]:
    try:
        start = datetime.strptime(anchor_date, "%Y-%m-%d")
    except ValueError:
        start = datetime.now()
    monday = start - timedelta(days=start.weekday())
    return [(monday + timedelta(days=offset)).strftime("%Y-%m-%d") for offset in range(7)]
