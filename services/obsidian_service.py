from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config.settings import OBSIDIAN_EXPORT_NOTES_DIR, OBSIDIAN_VAULT_PATH


def export_notes_to_obsidian(notes: list[dict]) -> dict:
    vault_path = Path(OBSIDIAN_VAULT_PATH).expanduser() if OBSIDIAN_VAULT_PATH else None
    if vault_path is None or not str(vault_path).strip():
        return {
            "ok": False,
            "error": (
                "Путь к Obsidian vault не настроен. "
                "Добавь OBSIDIAN_VAULT_PATH в .env."
            ),
        }

    if not vault_path.exists() or not vault_path.is_dir():
        return {
            "ok": False,
            "error": (
                "Путь к Obsidian vault не найден. "
                "Проверь OBSIDIAN_VAULT_PATH."
            ),
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
