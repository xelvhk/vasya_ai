from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.obsidian_knowledge_service import (
    RECOMMENDED_COMMUNITY_PLUGINS,
    audit_metadata_standards,
    autofix_metadata_standards,
    bootstrap_managed_vault,
    build_vault_health_report,
    build_graph_connectivity_report,
    build_vault_index,
    ensure_navigation_scaffold,
    rename_idea_notes_from_content,
    setup_recommended_plugins,
    strengthen_graph_links,
    triage_unstructured_ideas,
    write_vault_health_note,
)


class ObsidianKnowledgeServiceTests(unittest.TestCase):
    def test_bootstrap_creates_managed_structure_and_templates(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            result = bootstrap_managed_vault(vault)
            self.assertTrue(result["ok"])
            self.assertTrue((vault / "00_Inbox").exists())
            self.assertTrue((vault / "99_Templates" / "Project.md").exists())

    def test_plugin_setup_writes_community_plugins_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            vault.mkdir(parents=True, exist_ok=True)
            result = setup_recommended_plugins(vault)
            self.assertTrue(result["ok"])
            content = (vault / ".obsidian" / "community-plugins.json").read_text(encoding="utf-8")
            for plugin_id in RECOMMENDED_COMMUNITY_PLUGINS:
                self.assertIn(plugin_id, content)

    def test_build_index_extracts_frontmatter_and_links(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            note = vault / "03_Knowledge" / "RAG.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text(
                """---
type: knowledge
status: active
tags:
  - rag
  - vasya
---

# RAG

Связано с [[Vasya_AI]] и [[Obsidian]].
""",
                encoding="utf-8",
            )

            result = build_vault_index(vault)
            self.assertTrue(result["ok"])
            self.assertEqual(result["count"], 1)
            item = result["items"][0]
            self.assertEqual(item["note_type"], "knowledge")
            self.assertIn("Vasya_AI", item["links"])

    def test_triage_unstructured_ideas_adds_frontmatter(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            ideas_dir = vault / "03_Knowledge" / "Неразобранные идеи"
            ideas_dir.mkdir(parents=True, exist_ok=True)
            note = ideas_dir / "idea.md"
            note.write_text("# Идея\n\n#todo\n\nКупить микрофон и дописать описание проекта.", encoding="utf-8")

            result = triage_unstructured_ideas(vault)
            self.assertTrue(result["ok"])
            self.assertEqual(result["updated"], 1)
            text = note.read_text(encoding="utf-8")
            self.assertIn("type: task", text)
            self.assertIn("action: expand", text)

    def test_graph_report_detects_unresolved_and_isolated(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            a = vault / "03_Knowledge" / "A.md"
            b = vault / "03_Knowledge" / "B.md"
            c = vault / "03_Knowledge" / "C.md"
            a.parent.mkdir(parents=True, exist_ok=True)
            a.write_text("Связано с [[B]] и [[Missing note]].\n", encoding="utf-8")
            b.write_text("Тут пусто.\n", encoding="utf-8")
            c.write_text("Изолированная заметка.\n", encoding="utf-8")

            report = build_graph_connectivity_report(vault)
            self.assertTrue(report["ok"])
            self.assertEqual(report["total_notes"], 3)
            self.assertGreaterEqual(report["unresolved_links"], 1)
            self.assertGreaterEqual(report["isolated"], 1)

    def test_strengthen_graph_links_repairs_and_adds_relations(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            knowledge = vault / "03_Knowledge"
            knowledge.mkdir(parents=True, exist_ok=True)
            (knowledge / "Base.md").write_text(
                """---
type: knowledge
tags:
  - ai
---
Опорная заметка.
""",
                encoding="utf-8",
            )
            target = knowledge / "Идея.md"
            target.write_text(
                """---
type: knowledge
tags:
  - ai
---
Связано с [[03_Knowledge/BASE]].
""",
                encoding="utf-8",
            )

            result = strengthen_graph_links(vault, dry_run=False, limit=10)
            self.assertTrue(result["ok"])
            self.assertGreaterEqual(result["changed_notes"], 1)
            updated = target.read_text(encoding="utf-8")
            self.assertIn("[[Base]]", updated)

    def test_rename_ideas_from_content_and_rewrite_links(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            ideas = vault / "03_Knowledge" / "Неразобранные идеи"
            ideas.mkdir(parents=True, exist_ok=True)
            note = ideas / "2024-10-10.md"
            note.write_text(
                """---
type: idea
---
# Купить микрофон для записи
""",
                encoding="utf-8",
            )
            index = vault / "Неразобранные идеи.md"
            index.write_text("См. [[2024-10-10]]\n", encoding="utf-8")

            dry = rename_idea_notes_from_content(vault, dry_run=True)
            self.assertTrue(dry["ok"])
            self.assertEqual(dry["count"], 1)

            applied = rename_idea_notes_from_content(vault, dry_run=False)
            self.assertTrue(applied["ok"])
            self.assertEqual(applied["renamed"], 1)
            self.assertTrue((ideas / "2024-10-10-купить-микрофон-для-записи.md").exists())
            updated_index = index.read_text(encoding="utf-8")
            self.assertIn("[[2024-10-10-купить-микрофон-для-записи]]", updated_index)

    def test_metadata_audit_and_autofix(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            note = vault / "03_Knowledge" / "note.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text("# Note\n", encoding="utf-8")

            before = audit_metadata_standards(vault)
            self.assertTrue(before["ok"])
            self.assertEqual(before["non_compliant"], 1)

            fix = autofix_metadata_standards(vault, dry_run=False, limit=10)
            self.assertTrue(fix["ok"])
            self.assertEqual(fix["changed"], 1)

            after = audit_metadata_standards(vault)
            self.assertEqual(after["non_compliant"], 0)

    def test_navigation_scaffold_creation(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            vault.mkdir(parents=True, exist_ok=True)
            result = ensure_navigation_scaffold(vault, dry_run=False)
            self.assertTrue(result["ok"])
            self.assertTrue((vault / "01_Projects" / "MOC — Projects.md").exists())
            self.assertTrue((vault / "03_Knowledge" / "MOC — Knowledge.md").exists())

    def test_health_report_and_note_generation(self) -> None:
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "Vault"
            note = vault / "03_Knowledge" / "A.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text(
                """---
type: knowledge
status: active
area: knowledge
created: 2026-01-01
updated: 2026-01-01
tags:
  - a
---
Текст.
""",
                encoding="utf-8",
            )
            report = build_vault_health_report(vault, stale_days=1)
            self.assertTrue(report["ok"])
            self.assertEqual(report["total_notes"], 1)
            written = write_vault_health_note(vault, stale_days=1)
            self.assertTrue(written["ok"])
            self.assertTrue((vault / "05_Logs" / "Vault Health.md").exists())


if __name__ == "__main__":
    unittest.main()
    rename_idea_notes_from_content,
