from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.video_analysis_service import (
    TranscriptSegment,
    VideoAnalysisError,
    extract_instagram_request,
    parse_subtitles,
    summarize_transcript,
    analyze_media,
    render_srt,
    download_public_instagram,
)


class VideoAnalysisServiceTests(unittest.TestCase):
    def test_instagram_url_is_canonical_and_question_is_preserved(self) -> None:
        url, question = extract_instagram_request(
            "Что говорят? https://www.instagram.com/reel/AbC_123/?igsh=secret"
        )
        self.assertEqual(url, "https://www.instagram.com/reel/AbC_123/")
        self.assertEqual(question, "Что говорят?")

    def test_untrusted_urls_are_rejected(self) -> None:
        for value in (
            "https://instagram.com.evil.test/reel/AbC/",
            "http://www.instagram.com/reel/AbC/",
            "https://user@www.instagram.com/reel/AbC/",
            "https://www.instagram.com/reel/../../etc/passwd",
            "https://www.instagram.com/private/AbC/",
        ):
            with self.subTest(value=value), self.assertRaises(VideoAnalysisError):
                extract_instagram_request(value)

    @patch("services.video_analysis_service.subprocess.run")
    def test_inaccessible_instagram_video_requests_file_without_cookies(self, run) -> None:
        run.return_value = SimpleNamespace(returncode=1)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(VideoAnalysisError, "Пришлите видеофайл"):
                download_public_instagram("https://www.instagram.com/reel/AbC/", Path(directory))
        self.assertNotIn("--cookies-from-browser", run.call_args.args[0])
        self.assertNotIn("--cookies", run.call_args.args[0])
        self.assertIn("--ignore-config", run.call_args.args[0])

    def test_srt_and_vtt_keep_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            srt = Path(directory) / "clip.srt"
            srt.write_text(
                "1\n00:00:01,200 --> 00:00:03,400\nПервый тезис.\n\n"
                "2\n00:00:04,000 --> 00:00:05,000\nВторой тезис.\n",
                encoding="utf-8",
            )
            segments = parse_subtitles(srt)
            self.assertEqual([(s.start, s.end, s.text) for s in segments], [
                (1.2, 3.4, "Первый тезис."), (4.0, 5.0, "Второй тезис."),
            ])
            vtt = Path(directory) / "clip.vtt"
            vtt.write_text(
                "WEBVTT\n\n00:01.000 --> 00:02.500\nПривет <b>мир</b>.\n",
                encoding="utf-8",
            )
            self.assertEqual(parse_subtitles(vtt)[0].text, "Привет мир.")
            self.assertIn("00:00:01,200 --> 00:00:03,400", render_srt(segments))

    @patch("services.video_analysis_service.summarize_transcript", return_value=None)
    @patch("voice.stt.transcribe_timed", return_value=((0.2, 0.8, "Тестовая речь."),))
    def test_real_ffmpeg_pipeline_keeps_timed_transcript(self, _stt, _summary) -> None:
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory) / "clip.mp4"
            subprocess.run([
                "ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
                "-i", "color=c=black:s=16x16:d=1", "-f", "lavfi",
                "-i", "sine=frequency=440:duration=1", "-c:v", "mpeg4",
                "-c:a", "aac", "-shortest", str(media),
            ], check=True, capture_output=True, timeout=15)
            result = analyze_media(media)
            self.assertIn("[00:00] Тестовая речь.", result.response)
            self.assertTrue((Path(directory) / "clip.wav").is_file())

    @patch("services.video_analysis_service.summarize_transcript", return_value=None)
    @patch("voice.stt.transcribe_timed")
    def test_available_subtitles_do_not_run_speech_recognition(self, stt, _summary) -> None:
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory) / "clip.mp4"
            media.write_bytes(b"video")
            subtitle = Path(directory) / "clip.srt"
            subtitle.write_text("1\n00:00:01,000 --> 00:00:02,000\nПервый тезис.\n", encoding="utf-8")
            with patch("services.video_analysis_service._probe_media", return_value=(3.0, False)):
                result = analyze_media(media, subtitles=subtitle)
        self.assertEqual(result.subtitle_origin, "original")
        stt.assert_not_called()

    @patch("services.video_analysis_service.resolve_chat_model", return_value="local-test")
    @patch("services.video_analysis_service.generate")
    def test_summary_requires_exact_quote_in_cited_segment(self, generate, _model) -> None:
        segments = (TranscriptSegment(1.0, 3.0, "Контекст хранится на домашнем сервере."),)
        generate.return_value = (
            '{"answer":"Контекст хранится на домашнем сервере.",'
            '"segment":1,"quote":"Контекст хранится на домашнем сервере."}'
        )
        self.assertIn("[00:01]", summarize_transcript(segments, "Где контекст?"))
        generate.return_value = (
            '{"answer":"Контекст в облаке.","segment":1,"quote":"В облаке."}'
        )
        self.assertIsNone(summarize_transcript(segments, "Где контекст?"))


if __name__ == "__main__":
    unittest.main()
