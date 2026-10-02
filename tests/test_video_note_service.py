from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.video_note_service import VideoNoteError, save_video_note
from services.allowed_knowledge_index_service import search_indexed_notes


class VideoNoteServiceTests(unittest.TestCase):
    def test_save_is_stable_and_inside_allowed_vault_folder(self) -> None:
        with TemporaryDirectory() as directory:
            vault = Path(directory) / "My Vault"
            (vault / "30_Knowledge").mkdir(parents=True)
            video_id = "a" * 64
            first = save_video_note(
                video_id=video_id, source_url=None, summary="Первый ответ.",
                subtitle_srt="1\n00:00:01,000 --> 00:00:02,000\nПривет\n",
                subtitle_origin="transcribed", vault_path=vault,
            )
            second = save_video_note(
                video_id=video_id, source_url=None, summary="Обновлённый ответ.",
                subtitle_srt="1\n00:00:01,000 --> 00:00:02,000\nНовый текст\n",
                subtitle_origin="transcribed", vault_path=vault,
            )
            note = vault / first.relative_path
            self.assertEqual(first.relative_path, second.relative_path)
            self.assertEqual(len(list((vault / "30_Knowledge/Video").glob("*.md"))), 1)
            self.assertIn("Обновлённый ответ.", note.read_text(encoding="utf-8"))
            self.assertIn("Новый текст", note.read_text(encoding="utf-8"))
            self.assertIn("obsidian://open?", first.url)
            hits = search_indexed_notes(
                "Новый текст", vault_path=vault, index_path=Path(directory) / "index.sqlite3",
                refresh_after_seconds=0,
            ).hits
            self.assertEqual(hits[0].relative_path, first.relative_path)

    def test_symlinked_video_folder_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            outside = Path(directory) / "outside"
            (vault / "30_Knowledge").mkdir(parents=True)
            outside.mkdir()
            (vault / "30_Knowledge/Video").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(VideoNoteError):
                save_video_note(
                    video_id="b" * 64, source_url=None, summary="Текст",
                    subtitle_srt="1\n00:00:01,000 --> 00:00:02,000\nПривет\n",
                    subtitle_origin="transcribed", vault_path=vault,
                )
            self.assertEqual(list(outside.iterdir()), [])

    def test_source_url_must_match_video_id(self) -> None:
        with TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            (vault / "30_Knowledge").mkdir(parents=True)
            with self.assertRaises(VideoNoteError):
                save_video_note(
                    video_id="c" * 64, source_url="https://www.instagram.com/reel/ABC/",
                    summary="Текст", subtitle_srt="1\n00:00:01,000 --> 00:00:02,000\nПривет\n",
                    subtitle_origin="original", vault_path=vault,
                )


if __name__ == "__main__":
    unittest.main()
