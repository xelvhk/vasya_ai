import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.main import app


def test_save_video_note_from_preview_returns_obsidian_link() -> None:
    with TemporaryDirectory() as directory:
        vault = Path(directory) / "Test Vault"
        (vault / "30_Knowledge").mkdir(parents=True)
        video_id = hashlib.sha256(b"sample-video").hexdigest()
        with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
            "services.video_note_service.resolve_knowledge_vault_path", return_value=vault
        ):
            with TestClient(app) as client:
                response = client.post("/v1/video/save-note", json={
                    "video_id": video_id,
                    "summary": "Краткое содержание.",
                    "subtitle_srt": "1\n00:00:01,000 --> 00:00:02,000\nПервая мысль\n",
                    "subtitle_origin": "transcribed",
                })
        assert response.status_code == 200
        payload = response.json()
        assert payload["relative_path"].startswith("30_Knowledge/Video/")
        assert payload["url"].startswith("obsidian://open?")
        assert (vault / payload["relative_path"]).is_file()


def test_save_video_note_requires_auth() -> None:
    with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", True), patch(
        "apps.api.deps.VASYA_API_AUTH_TOKEN", "secret"
    ):
        with TestClient(app) as client:
            response = client.post("/v1/video/save-note", json={
                "video_id": "a" * 64, "summary": "Текст",
                "subtitle_srt": "1\n00:00:01,000 --> 00:00:02,000\nДа\n",
                "subtitle_origin": "original",
            })
    assert response.status_code == 401
