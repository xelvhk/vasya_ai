from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.obsidian_knowledge_service import (
    RECOMMENDED_COMMUNITY_PLUGINS,
    bootstrap_managed_vault,
    build_vault_index,
    setup_recommended_plugins,
    triage_unstructured_ideas,
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


if __name__ == "__main__":
    unittest.main()
