from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.allowed_knowledge_index_service import search_indexed_notes, sync_allowed_index


class AllowedKnowledgeIndexTests(unittest.TestCase):
    def test_sync_add_update_delete_and_reopen_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            vault = base / "vault"
            folder = vault / "30_Knowledge"
            folder.mkdir(parents=True)
            note = folder / "Topic.md"
            note.write_text("Сервер хранит индекс альфа.", encoding="utf-8")
            index = base / "knowledge.db"

            first = sync_allowed_index(vault_path=vault, index_path=index)
            self.assertEqual((first.added, first.updated, first.deleted), (1, 0, 0))
            self.assertEqual(len(search_indexed_notes("альфа", vault_path=vault, index_path=index, refresh_after_seconds=None).hits), 1)
            repeat = sync_allowed_index(vault_path=vault, index_path=index)
            self.assertEqual((repeat.added, repeat.updated, repeat.deleted, repeat.unchanged), (0, 0, 0, 1))

            note.write_text("Сервер хранит индекс бета.", encoding="utf-8")
            second = sync_allowed_index(vault_path=vault, index_path=index)
            self.assertEqual((second.added, second.updated, second.deleted), (0, 1, 0))
            self.assertEqual(search_indexed_notes("альфа", vault_path=vault, index_path=index, refresh_after_seconds=None).hits, ())
            self.assertEqual(len(search_indexed_notes("бета", vault_path=vault, index_path=index, refresh_after_seconds=None).hits), 1)

            note.unlink()
            third = sync_allowed_index(vault_path=vault, index_path=index)
            self.assertEqual((third.added, third.updated, third.deleted), (0, 0, 1))
            self.assertEqual(search_indexed_notes("бета", vault_path=vault, index_path=index, refresh_after_seconds=None).hits, ())

    def test_disallowed_and_escaping_symlink_are_not_stored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            vault = base / "vault"
            allowed = vault / "10_Projects" / "Active"
            allowed.mkdir(parents=True)
            private = vault / "20_Areas" / "Personal"
            private.mkdir(parents=True)
            (private / "Private.md").write_text("Секретная метка Гамма", encoding="utf-8")
            (allowed / "link.md").symlink_to(private / "Private.md")
            index = base / "knowledge.db"

            report = sync_allowed_index(vault_path=vault, index_path=index)
            result = search_indexed_notes("Гамма", vault_path=vault, index_path=index, refresh_after_seconds=None)

        self.assertIsNone(report.error)
        self.assertEqual(report.added, 0)
        self.assertEqual(result.hits, ())

    def test_search_refreshes_changed_and_deleted_files_when_due(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            vault = base / "vault"
            folder = vault / "30_Knowledge"
            folder.mkdir(parents=True)
            note = folder / "Topic.md"
            note.write_text("Первая версия контекста.", encoding="utf-8")
            index = base / "knowledge.db"

            initial = search_indexed_notes("версия", vault_path=vault, index_path=index)
            self.assertEqual(len(initial.hits), 1)
            note.write_text("Вторая редакция контекста.", encoding="utf-8")
            refreshed = search_indexed_notes("редакция", vault_path=vault, index_path=index, refresh_after_seconds=0)
            self.assertEqual(len(refreshed.hits), 1)
            self.assertEqual(search_indexed_notes("версия", vault_path=vault, index_path=index, refresh_after_seconds=None).hits, ())

            note.unlink()
            deleted = search_indexed_notes("редакция", vault_path=vault, index_path=index, refresh_after_seconds=0)
            self.assertEqual(deleted.hits, ())
            self.assertFalse(deleted.stale)

    def test_unavailable_vault_keeps_snapshot_marked_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            vault = base / "vault"
            folder = vault / "30_Knowledge"
            folder.mkdir(parents=True)
            (folder / "Topic.md").write_text("Снимок доступен офлайн.", encoding="utf-8")
            index = base / "knowledge.db"
            sync_allowed_index(vault_path=vault, index_path=index)
            folder.rename(base / "detached")
            result = search_indexed_notes("Снимок", vault_path=vault, index_path=index, refresh_after_seconds=0)

        self.assertEqual(len(result.hits), 1)
        self.assertTrue(result.stale)
        self.assertIsNotNone(result.observed_at)


if __name__ == "__main__":
    unittest.main()
