from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.allowed_knowledge_service import search_allowed_notes


class AllowedKnowledgeSearchTests(unittest.TestCase):
    def test_search_returns_excerpt_and_relative_source_only_from_allowed_folders(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            allowed = vault / "30_Knowledge" / "AI"
            allowed.mkdir(parents=True)
            (allowed / "RAG.md").write_text(
                "# RAG\nПоиск использует локальный индекс заметок.\n", encoding="utf-8"
            )
            disallowed = vault / "20_Areas" / "Personal"
            disallowed.mkdir(parents=True)
            (disallowed / "Private.md").write_text(
                "Локальный индекс содержит личные данные.\n", encoding="utf-8"
            )

            result = search_allowed_notes("локальный индекс", vault_path=vault)

        self.assertIsNone(result.error)
        self.assertEqual(len(result.hits), 1)
        self.assertEqual(result.hits[0].relative_path, "30_Knowledge/AI/RAG.md")
        self.assertIn("локальный индекс", result.hits[0].excerpt)
        self.assertTrue(result.hits[0].url.startswith("obsidian://open?"))

    def test_symlink_outside_allowed_folder_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            vault = base / "vault"
            allowed = vault / "10_Projects" / "Active"
            allowed.mkdir(parents=True)
            secret = base / "secret.md"
            secret.write_text("Секретный проект Гамма", encoding="utf-8")
            (allowed / "link.md").symlink_to(secret)

            result = search_allowed_notes("секретный Гамма", vault_path=vault)

        self.assertEqual(result.hits, ())

    def test_missing_vault_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = search_allowed_notes("проект", vault_path=Path(directory) / "missing")
        self.assertEqual(result.hits, ())
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
