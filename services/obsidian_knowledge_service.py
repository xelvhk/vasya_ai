from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
import unicodedata


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
    "99_Templates/Weekly-Review.md": """---
type: review
status: active
area: weekly
tags:
  - review
  - weekly
created: "{today}"
updated: "{today}"
---

# Weekly Review {{week}}

## Что сделано
- 

## Что не закрыто
- [ ] 

## Осиротевшие заметки / битые ссылки
- 

## Фокус следующей недели
- [ ] 
""",
    "99_Templates/MOC.md": """---
type: moc
status: active
area: knowledge
tags:
  - moc
created: "{today}"
updated: "{today}"
---

# {{title}}

## Разделы
- 

## Быстрые ссылки
- 
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


@dataclass(frozen=True)
class GraphNoteStats:
    path: Path
    title: str
    note_type: str
    tags: tuple[str, ...]
    links: tuple[str, ...]
    inbound: int
    outbound: int


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


def ensure_navigation_scaffold(vault_path: Path, *, dry_run: bool = True) -> dict:
    resolved = Path(vault_path).expanduser()
    if not resolved.exists() or not resolved.is_dir():
        return {"ok": False, "error": f"Vault path not found: {resolved}"}

    today = date.today().isoformat()
    scaffold: dict[str, str] = {
        "01_Projects/MOC — Projects.md": _moc_body("MOC — Projects", today, "projects"),
        "03_Knowledge/MOC — Knowledge.md": _moc_body("MOC — Knowledge", today, "knowledge"),
        "04_Tasks/MOC — Tasks.md": _moc_body("MOC — Tasks", today, "tasks"),
        "05_Logs/MOC — Weekly Review.md": _weekly_moc_body(today),
    }
    created: list[str] = []
    for relpath, body in scaffold.items():
        path = resolved / relpath
        if path.exists():
            continue
        created.append(relpath)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
    return {"ok": True, "dry_run": dry_run, "created": created}


def audit_metadata_standards(
    vault_path: Path,
    *,
    required_fields: tuple[str, ...] = ("type", "status", "area", "created", "updated", "tags"),
) -> dict:
    resolved = Path(vault_path).expanduser()
    if not resolved.exists() or not resolved.is_dir():
        return {"ok": False, "error": f"Vault path not found: {resolved}"}

    checked = 0
    missing_total = 0
    missing_by_field: dict[str, int] = {}
    missing_by_file: list[dict[str, object]] = []

    for note_path in resolved.rglob("*.md"):
        if ".obsidian" in note_path.parts:
            continue
        checked += 1
        text = note_path.read_text(encoding="utf-8", errors="ignore")
        fm, _body = _extract_frontmatter(text)
        missing = [field for field in required_fields if not _has_frontmatter_field(fm, field)]
        if not missing:
            continue
        missing_total += len(missing)
        for field in missing:
            missing_by_field[field] = missing_by_field.get(field, 0) + 1
        missing_by_file.append({"path": str(note_path), "missing": missing})

    compliant = checked - len(missing_by_file)
    return {
        "ok": True,
        "checked": checked,
        "compliant": compliant,
        "non_compliant": len(missing_by_file),
        "missing_total": missing_total,
        "missing_by_field": missing_by_field,
        "sample_non_compliant": missing_by_file[:50],
    }


def autofix_metadata_standards(
    vault_path: Path,
    *,
    dry_run: bool = True,
    limit: int = 500,
    required_fields: tuple[str, ...] = ("type", "status", "area", "created", "updated", "tags"),
) -> dict:
    resolved = Path(vault_path).expanduser()
    if not resolved.exists() or not resolved.is_dir():
        return {"ok": False, "error": f"Vault path not found: {resolved}"}

    changed = 0
    preview: list[dict[str, object]] = []
    max_count = max(1, int(limit))
    for note_path in resolved.rglob("*.md"):
        if ".obsidian" in note_path.parts:
            continue
        if changed >= max_count:
            break
        text = note_path.read_text(encoding="utf-8", errors="ignore")
        fm, body = _extract_frontmatter(text)
        original_fm = dict(fm)
        fm = _fill_standard_frontmatter(fm, note_path, required_fields=required_fields)
        if fm == original_fm:
            continue
        changed += 1
        preview.append({"path": str(note_path), "added": sorted(set(fm.keys()) - set(original_fm.keys()))})
        if not dry_run:
            payload = _compose_frontmatter_block(fm)
            rebuilt = payload + "\n\n" + body.lstrip("\n")
            note_path.write_text(rebuilt, encoding="utf-8")

    return {"ok": True, "dry_run": dry_run, "changed": changed, "preview": preview[:80]}


def build_vault_health_report(
    vault_path: Path,
    *,
    stale_days: int = 30,
) -> dict:
    resolved = Path(vault_path).expanduser()
    if not resolved.exists() or not resolved.is_dir():
        return {"ok": False, "error": f"Vault path not found: {resolved}"}

    graph = build_graph_connectivity_report(resolved)
    audit = audit_metadata_standards(resolved)
    stats, unresolved = _collect_graph_stats(resolved)

    today_ord = date.today().toordinal()
    stale: list[str] = []
    no_parent: list[str] = []
    no_backlinks: list[str] = []
    type_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    for item in stats:
        text = item.path.read_text(encoding="utf-8", errors="ignore")
        fm, _ = _extract_frontmatter(text)
        note_type = str(fm.get("type") or item.note_type or "note").strip().lower()
        status = str(fm.get("status") or "active").strip().lower()
        type_counts[note_type] = type_counts.get(note_type, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

        if not _has_frontmatter_field(fm, "parent"):
            no_parent.append(str(item.path))
        if item.inbound == 0:
            no_backlinks.append(str(item.path))
        updated = str(fm.get("updated") or "").strip()
        d = _parse_iso_date(updated)
        if d is not None and today_ord - d.toordinal() > max(1, stale_days):
            stale.append(str(item.path))

    return {
        "ok": True,
        "total_notes": len(stats),
        "graph": {
            "isolated": int(graph.get("isolated", 0)),
            "low_connected": int(graph.get("low_connected", 0)),
            "unresolved_links": int(graph.get("unresolved_links", 0)),
            "sample_unresolved": unresolved[:20],
        },
        "metadata": {
            "non_compliant": int(audit.get("non_compliant", 0)),
            "missing_by_field": dict(audit.get("missing_by_field", {})),
        },
        "hygiene": {
            "no_parent": len(no_parent),
            "no_backlinks": len(no_backlinks),
            "stale": len(stale),
            "sample_no_parent": no_parent[:30],
            "sample_no_backlinks": no_backlinks[:30],
            "sample_stale": stale[:30],
        },
        "taxonomy": {
            "type_counts": type_counts,
            "status_counts": status_counts,
        },
    }


def write_vault_health_note(
    vault_path: Path,
    *,
    stale_days: int = 30,
    target_relpath: str = "05_Logs/Vault Health.md",
) -> dict:
    resolved = Path(vault_path).expanduser()
    report = build_vault_health_report(resolved, stale_days=stale_days)
    if not report.get("ok"):
        return report
    target = resolved / target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = _render_vault_health_markdown(report, stale_days=stale_days)
    target.write_text(payload, encoding="utf-8")
    return {"ok": True, "path": str(target), "summary": report}


def rename_idea_notes_from_content(
    vault_path: Path,
    *,
    ideas_dir: str = "03_Knowledge/Неразобранные идеи",
    dry_run: bool = True,
    limit: int = 200,
) -> dict:
    resolved = Path(vault_path).expanduser()
    target_dir = resolved / ideas_dir
    if not target_dir.exists() or not target_dir.is_dir():
        return {"ok": False, "error": f"Ideas directory not found: {target_dir}"}

    notes = sorted(target_dir.rglob("*.md"))
    renames: list[tuple[Path, Path]] = []
    used_names: set[str] = {path.stem.lower() for path in notes}
    max_count = max(1, int(limit))

    for note_path in notes:
        if len(renames) >= max_count:
            break
        text = note_path.read_text(encoding="utf-8", errors="ignore")
        title = _extract_human_title(text)
        if not title:
            continue
        slug = _slugify_note_title(title)
        if not slug:
            continue
        date_prefix = _extract_date_prefix(note_path.stem)
        if date_prefix and not slug.startswith(date_prefix):
            slug = f"{date_prefix}-{slug}"
        if slug.lower() == note_path.stem.lower():
            continue
        candidate = _make_unique_slug(slug, used_names)
        used_names.add(candidate.lower())
        renames.append((note_path, note_path.with_name(f"{candidate}.md")))

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "count": len(renames),
            "preview": [
                {"from": str(source), "to": str(target)}
                for source, target in renames[:80]
            ],
        }

    for source, target in renames:
        source.rename(target)

    updated_links = _rewrite_links_after_renames(resolved, renames, ideas_dir=ideas_dir)
    return {
        "ok": True,
        "dry_run": False,
        "renamed": len(renames),
        "updated_link_files": updated_links,
        "preview": [
            {"from": str(source), "to": str(target)}
            for source, target in renames[:80]
        ],
    }


def build_graph_connectivity_report(vault_path: Path) -> dict:
    resolved = Path(vault_path).expanduser()
    if not resolved.exists() or not resolved.is_dir():
        return {"ok": False, "error": f"Vault path not found: {resolved}"}

    stats, unresolved = _collect_graph_stats(resolved)
    isolated = [item for item in stats if item.inbound == 0 and item.outbound == 0]
    low_connected = [item for item in stats if item.inbound + item.outbound <= 1]

    return {
        "ok": True,
        "total_notes": len(stats),
        "unresolved_links": len(unresolved),
        "isolated": len(isolated),
        "low_connected": len(low_connected),
        "sample_isolated": [str(item.path) for item in isolated[:30]],
        "sample_unresolved": unresolved[:30],
    }


def strengthen_graph_links(
    vault_path: Path,
    *,
    dry_run: bool = True,
    limit: int = 100,
    include_prefixes: tuple[str, ...] = ("01_Projects", "03_Knowledge", "04_Tasks", "05_Logs"),
) -> dict:
    resolved = Path(vault_path).expanduser()
    if not resolved.exists() or not resolved.is_dir():
        return {"ok": False, "error": f"Vault path not found: {resolved}"}

    stats, unresolved = _collect_graph_stats(resolved)
    title_index = _build_title_index(stats)
    note_by_path = {item.path: item for item in stats}

    applied = 0
    link_repairs = 0
    relation_additions = 0
    preview: list[dict[str, object]] = []

    for item in stats:
        if applied >= max(1, int(limit)):
            break
        rel = item.path.relative_to(resolved).as_posix()
        if include_prefixes and not any(rel.startswith(prefix + "/") or rel == prefix for prefix in include_prefixes):
            continue
        note_text = item.path.read_text(encoding="utf-8", errors="ignore")
        updated_text = note_text
        changed = False
        note_repairs = 0
        note_relations = 0

        # Repair unresolved links when we can resolve by unique note title.
        for raw_target in item.links:
            normalized = _normalize_link_target(raw_target)
            candidates = title_index.get(normalized, ())
            if len(candidates) != 1:
                continue
            replacement = _path_to_wikilink(candidates[0], resolved)
            requires_normalize = "/" in raw_target or "\\" in raw_target
            unresolved_like = not _link_exists(raw_target, title_index)
            if not requires_normalize and not unresolved_like:
                continue
            patched = _replace_wikilink_target(updated_text, raw_target, replacement)
            if patched != updated_text:
                updated_text = patched
                changed = True
                link_repairs += 1
                note_repairs += 1

        # Add relation block for isolated/low-connected notes.
        fresh_meta = _parse_note(item.path)
        fresh_inbound = note_by_path[item.path].inbound
        low_connected = fresh_inbound + len(fresh_meta.links) <= 1
        if low_connected:
            related = _suggest_related_notes(item.path, fresh_meta, stats)
            if related:
                block = "Связано с " + ", ".join(f"[[{_path_to_wikilink(path, resolved)}]]" for path in related) + "."
                if block not in updated_text:
                    spacer = "\n" if updated_text.endswith("\n") else "\n\n"
                    updated_text = updated_text.rstrip() + spacer + "\n" + block + "\n"
                    changed = True
                    relation_additions += 1
                    note_relations += 1

        if changed:
            if not dry_run:
                item.path.write_text(updated_text, encoding="utf-8")
            applied += 1
            preview.append(
                {
                    "path": str(item.path),
                    "link_repairs": note_repairs,
                    "relation_additions": note_relations,
                }
            )

    return {
        "ok": True,
        "dry_run": dry_run,
        "total_notes": len(stats),
        "unresolved_before": len(unresolved),
        "changed_notes": applied,
        "link_repairs": link_repairs,
        "relation_additions": relation_additions,
        "preview": preview[:30],
    }


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


def _collect_graph_stats(vault_path: Path) -> tuple[list[GraphNoteStats], list[dict[str, str]]]:
    notes: list[ObsidianNoteMeta] = []
    path_by_title: dict[str, list[Path]] = {}
    path_set: set[Path] = set()
    for note_path in vault_path.rglob("*.md"):
        if ".obsidian" in note_path.parts:
            continue
        parsed = _parse_note(note_path)
        notes.append(parsed)
        path_set.add(note_path)
        key = _normalize_link_target(parsed.title)
        path_by_title.setdefault(key, []).append(note_path)
        stem_key = _normalize_link_target(note_path.stem)
        path_by_title.setdefault(stem_key, []).append(note_path)

    inbound_map: dict[Path, int] = {Path(item.path): 0 for item in notes}
    unresolved: list[dict[str, str]] = []
    for note in notes:
        source = Path(note.path)
        for target in note.links:
            resolved_target = _resolve_link_target(source, target, path_set, path_by_title)
            if resolved_target is None:
                unresolved.append({"source": str(source), "target": target})
                continue
            inbound_map[resolved_target] = inbound_map.get(resolved_target, 0) + 1

    stats = [
        GraphNoteStats(
            path=Path(item.path),
            title=item.title,
            note_type=item.note_type,
            tags=item.tags,
            links=item.links,
            inbound=inbound_map.get(Path(item.path), 0),
            outbound=len(item.links),
        )
        for item in notes
    ]
    return stats, unresolved


def _resolve_link_target(
    source: Path,
    target: str,
    path_set: set[Path],
    path_by_title: dict[str, list[Path]],
) -> Path | None:
    raw = target.replace("\\", "/").strip()
    if not raw:
        return None
    candidate = (source.parent / f"{raw}.md").resolve()
    if candidate in path_set:
        return candidate
    normalized = _normalize_link_target(raw)
    candidates = path_by_title.get(normalized, [])
    if len(candidates) >= 1:
        return candidates[0]
    return None


def _normalize_link_target(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    if "/" in normalized:
        normalized = normalized.split("/")[-1]
    return normalized.removesuffix(".md").strip().lower()


def _build_title_index(stats: list[GraphNoteStats]) -> dict[str, tuple[Path, ...]]:
    index: dict[str, list[Path]] = {}
    for item in stats:
        index.setdefault(_normalize_link_target(item.title), []).append(item.path)
        index.setdefault(_normalize_link_target(item.path.stem), []).append(item.path)
    return {key: tuple(dict.fromkeys(paths)) for key, paths in index.items()}


def _link_exists(target: str, title_index: dict[str, tuple[Path, ...]]) -> bool:
    return _normalize_link_target(target) in title_index


def _replace_wikilink_target(text: str, old_target: str, new_target: str) -> str:
    escaped = re.escape(old_target)
    pattern = re.compile(rf"\[\[\s*{escaped}(\s*[|#][^\]]*)?\]\]")
    return pattern.sub(lambda m: f"[[{new_target}{m.group(1) or ''}]]", text)


def _path_to_wikilink(path: Path, vault_path: Path) -> str:
    _ = vault_path
    return path.stem


def _suggest_related_notes(
    note_path: Path,
    note_meta: ObsidianNoteMeta,
    stats: list[GraphNoteStats],
) -> list[Path]:
    related: list[Path] = []
    current_tags = set(tag.lower() for tag in note_meta.tags)
    for candidate in stats:
        if candidate.path == note_path:
            continue
        shared = current_tags.intersection(tag.lower() for tag in candidate.tags)
        same_type = note_meta.note_type == candidate.note_type and note_meta.note_type not in {"note", ""}
        if shared or same_type:
            related.append(candidate.path)
        if len(related) >= 2:
            break
    return related


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


def _extract_human_title(text: str) -> str:
    _fm, body = _extract_frontmatter(text)
    lines = body.splitlines()
    first_meaningful = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading and not _looks_like_date_label(heading):
                return heading
            if heading and not first_meaningful:
                first_meaningful = heading
            continue
        if stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
            candidate = stripped[5:].strip()
        else:
            candidate = stripped
        if candidate and not _looks_like_date_label(candidate):
            return re.sub(r"\s+", " ", candidate)[:80].strip()
        if candidate and not first_meaningful:
            first_meaningful = candidate
    return re.sub(r"\s+", " ", first_meaningful)[:80].strip() if first_meaningful else ""


def _slugify_note_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).strip().lower()
    normalized = re.sub(r"[\"'`«»“”]", "", normalized)
    normalized = re.sub(r"[\(\)\[\]\{\}:;!?]", " ", normalized)
    normalized = re.sub(r"[\\/|]+", " ", normalized)
    normalized = re.sub(r"\s+", "-", normalized).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    allowed = []
    for ch in normalized:
        if ch.isalnum() or ch in {"-", "_"}:
            allowed.append(ch)
    return "".join(allowed).strip("-_")


def _looks_like_date_label(value: str) -> bool:
    low = value.strip().lower()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}([ _\-\(\)\d]*)?", low):
        return True
    if re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}([ _\-\(\)\d]*)?", low):
        return True
    return False


def _extract_date_prefix(stem: str) -> str:
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", stem)
    return match.group(1) if match else ""


def _make_unique_slug(base: str, used: set[str]) -> str:
    candidate = base
    idx = 2
    while candidate.lower() in used:
        candidate = f"{base}-{idx}"
        idx += 1
    return candidate


def _rewrite_links_after_renames(vault_path: Path, renames: list[tuple[Path, Path]], *, ideas_dir: str) -> int:
    if not renames:
        return 0
    by_old_stem = {old.stem: new.stem for old, new in renames}
    ideas_dir_norm = ideas_dir.replace("\\", "/")
    by_old_path = {
        f"{ideas_dir_norm}/{old.stem}": new.stem
        for old, new in renames
    }

    updated_files = 0
    for md in vault_path.rglob("*.md"):
        if ".obsidian" in md.parts:
            continue
        text = md.read_text(encoding="utf-8", errors="ignore")
        updated = text
        for old_stem, new_stem in by_old_stem.items():
            updated = _replace_wikilink_target(updated, old_stem, new_stem)
        for old_path, new_stem in by_old_path.items():
            updated = _replace_wikilink_target(updated, old_path, new_stem)
        if updated != text:
            md.write_text(updated, encoding="utf-8")
            updated_files += 1
    return updated_files


def _moc_body(title: str, today: str, area: str) -> str:
    return (
        f"---\n"
        f"type: moc\n"
        f"status: active\n"
        f"area: {area}\n"
        f"tags:\n"
        f"  - moc\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"## Разделы\n"
        f"- \n\n"
        f"## Быстрые ссылки\n"
        f"- \n"
    )


def _weekly_moc_body(today: str) -> str:
    return (
        f"---\n"
        f"type: moc\n"
        f"status: active\n"
        f"area: logs\n"
        f"tags:\n"
        f"  - moc\n"
        f"  - weekly\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        f"---\n\n"
        f"# MOC — Weekly Review\n\n"
        f"## Недели\n"
        f"- \n\n"
        f"## Сводки\n"
        f"- \n"
    )


def _has_frontmatter_field(frontmatter: dict, field: str) -> bool:
    value = frontmatter.get(field)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return True


def _fill_standard_frontmatter(
    frontmatter: dict[str, object],
    note_path: Path,
    *,
    required_fields: tuple[str, ...],
) -> dict[str, object]:
    fm = dict(frontmatter)
    today = date.today().isoformat()
    inferred_type = str(fm.get("type") or _infer_type_from_path(note_path)).strip().lower()
    if "type" in required_fields and not _has_frontmatter_field(fm, "type"):
        fm["type"] = inferred_type
    if "status" in required_fields and not _has_frontmatter_field(fm, "status"):
        fm["status"] = "todo" if inferred_type == "task" else "active"
    if "area" in required_fields and not _has_frontmatter_field(fm, "area"):
        fm["area"] = _infer_area_from_path(note_path)
    if "created" in required_fields and not _has_frontmatter_field(fm, "created"):
        fm["created"] = today
    if "updated" in required_fields and not _has_frontmatter_field(fm, "updated"):
        fm["updated"] = today
    if "tags" in required_fields and not _has_frontmatter_field(fm, "tags"):
        fm["tags"] = [inferred_type if inferred_type else "note"]
    return fm


def _infer_type_from_path(note_path: Path) -> str:
    parts = set(note_path.parts)
    if "04_Tasks" in parts:
        return "task"
    if "01_Projects" in parts:
        return "project"
    if "03_Knowledge" in parts:
        return "knowledge"
    if "05_Logs" in parts:
        return "log"
    if "99_Templates" in parts:
        return "template"
    return "note"


def _infer_area_from_path(note_path: Path) -> str:
    parts = set(note_path.parts)
    if "01_Projects" in parts:
        return "projects"
    if "02_Areas" in parts:
        return "areas"
    if "03_Knowledge" in parts:
        return "knowledge"
    if "04_Tasks" in parts:
        return "tasks"
    if "05_Logs" in parts:
        return "logs"
    if "99_Templates" in parts:
        return "templates"
    if "00_Inbox" in parts:
        return "inbox"
    return "general"


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        return None


def _render_vault_health_markdown(report: dict, *, stale_days: int) -> str:
    today = date.today().isoformat()
    total = int(report.get("total_notes", 0))
    graph = report.get("graph", {})
    meta = report.get("metadata", {})
    hygiene = report.get("hygiene", {})
    taxonomy = report.get("taxonomy", {})

    lines = [
        "---",
        "type: report",
        "status: active",
        "area: logs",
        f"created: {today}",
        f"updated: {today}",
        "tags:",
        "  - health",
        "  - vault",
        "---",
        "",
        "# Vault Health",
        "",
        f"- Total notes: {total}",
        f"- Isolated: {int(graph.get('isolated', 0))}",
        f"- Low connected: {int(graph.get('low_connected', 0))}",
        f"- Broken links: {int(graph.get('unresolved_links', 0))}",
        f"- Metadata non-compliant: {int(meta.get('non_compliant', 0))}",
        f"- No parent: {int(hygiene.get('no_parent', 0))}",
        f"- No backlinks: {int(hygiene.get('no_backlinks', 0))}",
        f"- Stale (>{stale_days} days): {int(hygiene.get('stale', 0))}",
        "",
        "## Type Counts",
    ]
    for key, value in sorted(dict(taxonomy.get("type_counts", {})).items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Status Counts"])
    for key, value in sorted(dict(taxonomy.get("status_counts", {})).items()):
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Sample Broken Links"])
    for row in list(graph.get("sample_unresolved", []))[:15]:
        src = str(row.get("source", ""))
        tgt = str(row.get("target", ""))
        lines.append(f"- `{src}` -> `{tgt}`")

    lines.extend(["", "## Sample No Parent"])
    for path in list(hygiene.get("sample_no_parent", []))[:15]:
        lines.append(f"- `{path}`")

    lines.extend(["", "## Sample No Backlinks"])
    for path in list(hygiene.get("sample_no_backlinks", []))[:15]:
        lines.append(f"- `{path}`")

    lines.extend(["", "## Sample Stale"])
    for path in list(hygiene.get("sample_stale", []))[:15]:
        lines.append(f"- `{path}`")
    lines.append("")
    return "\n".join(lines)
