from __future__ import annotations

from pathlib import Path
import hashlib
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.main import app
from services.video_analysis_service import TranscriptSegment, VideoAnalysis


class VideoAgentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analysis = VideoAnalysis(
            "Краткий ответ [00:01]\n\nРасшифровка:\n[00:01] Первый тезис.",
            "https://www.instagram.com/reel/AbC123/",
            "transcribed",
            (TranscriptSegment(1.0, 2.0, "Первый тезис."),),
        )

    @patch("apps.api.routes.chat.analyze_instagram_request")
    def test_video_chat_accepts_instagram_link(self, analyze) -> None:
        analyze.return_value = self.analysis
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.main.log_interaction_event"
        ), patch("apps.api.routes.chat.log_interaction_event"):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/chat",
                    json={"agent": "video", "text": "Что говорят? https://instagram.com/reel/AbC123/"},
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "video_analysis")
        self.assertEqual(response.json()["sources"][0]["url"], self.analysis.source_url)
        self.assertIn("00:00:01,000 --> 00:00:02,000", response.json()["subtitle_srt"])
        self.assertEqual(response.json()["video_id"], hashlib.sha256(self.analysis.source_url.encode()).hexdigest())
        analyze.assert_called_once()

    @patch("apps.api.routes.video.analyze_media")
    def test_raw_upload_returns_same_contract_and_deletes_temporary_file(self, analyze) -> None:
        analyze.return_value = VideoAnalysis("Расшифровка:\n[00:01] Первый тезис.", None, "transcribed", self.analysis.segments)
        observed_path: Path | None = None
        def inspect_file(path, **_kwargs):
            nonlocal observed_path
            observed_path = path
            self.assertEqual(path.read_bytes(), b"fake-video")
            return analyze.return_value
        analyze.side_effect = inspect_file
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.main.log_interaction_event"
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/video/upload",
                    content=b"fake-video",
                    headers={"content-type": "video/mp4", "x-video-extension": "mp4", "x-video-question": "%D0%9E%20%D1%87%D1%91%D0%BC%20%D0%B2%D0%B8%D0%B4%D0%B5%D0%BE"},
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "video_analysis")
        self.assertEqual(response.json()["sources"], [])
        self.assertEqual(response.json()["video_id"], hashlib.sha256(b"fake-video").hexdigest())
        self.assertIsNotNone(observed_path)
        self.assertFalse(observed_path.exists())

    def test_upload_rejects_unsupported_extension(self) -> None:
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.main.log_interaction_event"
        ):
            with TestClient(app) as client:
                response = client.post("/v1/video/upload", content=b"bad", headers={"x-video-extension": "txt"})
        self.assertEqual(response.status_code, 415)

    def test_upload_enforces_streaming_size_limit(self) -> None:
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "apps.api.main.log_interaction_event"
        ), patch("apps.api.routes.video.MAX_VIDEO_BYTES", 4):
            with TestClient(app) as client:
                response = client.post("/v1/video/upload", content=b"12345", headers={"x-video-extension": "mp4"})
        self.assertEqual(response.status_code, 413)

    def test_upload_requires_api_auth(self) -> None:
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", True), patch(
            "apps.api.deps.VASYA_API_AUTH_TOKEN", "test-token"
        ), patch("apps.api.main.log_interaction_event"):
            with TestClient(app) as client:
                response = client.post("/v1/video/upload", content=b"video", headers={"x-video-extension": "mp4"})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
