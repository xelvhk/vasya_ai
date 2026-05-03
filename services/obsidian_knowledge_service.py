from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re


DEFAULT_FOLDERS: tuple[str, ...] = (
    "00_Inbox",
    "01_Projects",
    "02_Areas",
    "03_Knowledge",
    "04_Tasks",
    "05_Logs",
    "99_Templates",
)

DEFAULT_TEMPLATES: dict[str, str] = {
    "99_Templates/Project.md": """---
type: project
status: active
icon: "🤖"
tags:
  - project
created: "{today}"
---

# {{title}}

## Цель
- 

## Контекст

## Следующие шаги
- [ ] 

Связано с [[Vasya_AI]].
""",
    "99_Templates/Task.md": """---
type: task
status: todo
icon: "✅"
priority: medium
project: Vasya_AI
created: "{today}"
---

- [ ] {{task}}
""",
    "99_Templates/Knowledge.md": """---
type: knowledge
status: active
icon: "📘"
tags:
  - knowledge
created: "{today}"
---

# {{title}}

## Кратко

## Детали

Связано с [[Vasya_AI]].
""",
}

RECOMMENDED_COMMUNITY_PLUGINS: tuple[str, ...] = (
    "dataview",
    "obsidian-icon-folder",
    "templater-obsidian",
    "obsidian-tasks-plugin",
    "omnisearch",
    "juggl",
    "obsidian-excalibrain",
)

LINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")


@dataclass(frozen=True)
class ObsidianNoteMeta:
    path: str
    title: str
    note_type: str
    status: str
    tags: tuple[str, ...]
    links: tuple[str, ...]


def bootstrap_managed_vault(vault_path: Path) -> dict:
    resolved = Path(vault_path).expanduser()
    resolved.mkdir(parents=True, exist_ok=True)

    created_dirs = []
    for dirname in DEFAULT_FOLDERS:
        path = resolved / dirname
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(dirname)

    created_templates = []
    today = date.today().isoformat()
    for relpath, body_template in DEFAULT_TEMPLATES.items():
        path = resolved / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            continue
        body = body_template.format(today=today)
        path.write_text(body.strip() + "\n", encoding="utf-8")
        created_templates.append(relpath)

    return {
        "ok": True,
        "vault_path": str(resolved),
        "created_dirs": created_dirs,
        "created_templates": created_templates,
    }


def setup_recommended_plugins(vault_path: Path) -> dict:
    resolved = Path(vault_path).expanduser()
    obsidian_dir = resolved / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    plugins_path = obsidian_dir / "community-plugins.json"
    existing: list[str] = []
    if plugins_path.exists():
        try:
            loaded = json.loads(plugins_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = [str(item).strip() for item in loaded if str(item).strip()]
        except Exception:
            existing = []

    merged = list(dict.fromkeys(existing + list(RECOMMENDED_COMMUNITY_PLUGINS)))
    plugins_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "plugins_file": str(plugins_path),
        "plugins_count": len(merged),
    }


def build_vault_index(vault_path: Path, *, limit: int = 1000) -> dict:
    resolved = Path(vault_path).expanduser()
    if not resolved.exists() or not resolved.is_dir():
        return {"ok": False, "error": f"Vault path not found: {resolved}"}

    notes: list[ObsidianNoteMeta] = []
    for note_path in resolved.rglob("*.md"):
        if ".obsidian" in note_path.parts:
            continue
        parsed = _parse_note(note_path)
        notes.append(parsed)
        if len(notes) >= max(1, int(limit)):
            break

    type_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for item in notes:
        type_counts[item.note_type] = type_counts.get(item.note_type, 0) + 1
        status_counts[item.status] = status_counts.get(item.status, 0) + 1

    return {
        "ok": True,
        "count": len(notes),
        "type_counts": type_counts,
        "status_counts": status_counts,
        "items": [item.__dict__ for item in notes[:80]],
    }


def triage_unstructured_ideas(
    vault_path: Path,
    *,
    ideas_dir: str = "03_Knowledge/Неразобранные идеи",
) -> dict:
    resolved = Path(vault_path).expanduser()
    target_dir = resolved / ideas_dir
    if not target_dir.exists() or not target_dir.is_dir():
        return {"ok": False, "error": f"Ideas directory not found: {target_dir}"}

    updated = 0
    skipped = 0
    for note_path in target_dir.rglob("*.md"):
        text = note_path.read_text(encoding="utf-8", errors="ignore")
        frontmatter, _body = _extract_frontmatter(text)
        if frontmatter:
            skipped += 1
            continue
        class_meta = _classify_idea_text(text)
        payload = _compose_frontmatter_block(class_meta)
        note_path.write_text(payload + "\n\n" + text.lstrip("\n"), encoding="utf-8")
        updated += 1
    return {"ok": True, "updated": updated, "skipped": skipped, "ideas_dir": str(target_dir)}


def _parse_note(note_path: Path) -> ObsidianNoteMeta:
    text = note_path.read_text(encoding="utf-8", errors="ignore")
    frontmatter, body = _extract_frontmatter(text)

    title = str(frontmatter.get("title") or note_path.stem).strip()
    note_type = str(frontmatter.get("type") or "note").strip().lower()
    status = str(frontmatter.get("status") or "active").strip().lower()
    tags_raw = frontmatter.get("tags") or []
    if isinstance(tags_raw, str):
        tags = tuple(tag.strip() for tag in tags_raw.split(",") if tag.strip())
    elif isinstance(tags_raw, list):
        tags = tuple(str(tag).strip() for tag in tags_raw if str(tag).strip())
    else:
        tags = ()
    links = tuple(dict.fromkeys(LINK_PATTERN.findall(body)))

    return ObsidianNoteMeta(
        path=str(note_path),
        title=title,
        note_type=note_type,
        status=status,
        tags=tags,
        links=links,
    )


def _extract_frontmatter(text: str) -> tuple[dict, str]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, text

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text

    raw = "\n".join(lines[1:end]).strip()
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    parsed = _parse_simple_yaml_frontmatter(raw)
    return parsed, body


def _compose_frontmatter_block(meta: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _classify_idea_text(text: str) -> dict[str, object]:
    low = text.lower()
    note_type = "idea"
    status = "backlog"
    action = "review"
    tags = ["idea", "knowledge"]

    if "#todo" in low or "купить" in low:
        note_type = "task"
        status = "todo"
        action = "buy" if "купить" in low else "do"
        tags.append("todo")
    elif "проект" in low or "#project" in low:
        note_type = "project_idea"
        status = "draft"
        action = "structure"
        tags.append("project")

    if "дописать" in low:
        status = "draft"
        action = "expand"
        tags.append("expand")
    if "#для_фильма" in low or "фильм" in low:
        tags.append("film")
    if "#journal-import" in low:
        tags.append("journal_import")

    unique_tags = list(dict.fromkeys(tags))
    return {
        "type": note_type,
        "status": status,
        "icon": '"💡"',
        "action": action,
        "priority": "medium",
        "tags": unique_tags,
        "created": date.today().isoformat(),
    }


def _parse_simple_yaml_frontmatter(raw: str) -> dict:
    result: dict[str, object] = {}
    key: str | None = None
    for source_line in raw.splitlines():
        line = source_line.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and key:
            current = result.get(key)
            if not isinstance(current, list):
                current = []
            current.append(line[4:].strip().strip("'\""))
            result[key] = current
            continue
        if ":" not in line:
            continue
        left, right = line.split(":", 1)
        key = left.strip()
        value = right.strip().strip("'\"")
        if value == "":
            result[key] = []
        elif value.lower() in {"true", "false"}:
            result[key] = value.lower() == "true"
        else:
            result[key] = value
    return result
