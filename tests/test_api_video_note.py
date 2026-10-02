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


def test_server_queues_note_until_mac_confirms_matching_revision(tmp_path, monkeypatch) -> None:
    from services.video_note_service import save_video_note

    monkeypatch.setenv("VASYA_VIDEO_NOTE_QUEUE_MODE", "true")
    monkeypatch.setenv("VASYA_VIDEO_NOTE_QUEUE_FILE", str(tmp_path / "pending.db"))
    video_id = hashlib.sha256(b"queued-video").hexdigest()
    payload = {
        "video_id": video_id, "summary": "Первая версия",
        "source_url": None,
        "subtitle_srt": "1\n00:00:01,000 --> 00:00:02,000\nПривет\n",
        "subtitle_origin": "transcribed",
    }
    with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", True), patch(
        "apps.api.deps.VASYA_API_AUTH_TOKEN", "secret"
    ), TestClient(app) as client:
        headers = {"X-API-Key": "secret"}
        queued = client.post("/v1/video/save-note", json=payload, headers=headers)
        assert queued.status_code == 202
        assert queued.json()["status"] == "queued"
        assert queued.json()["url"] is None
        assert client.post("/v1/video/save-note", json=payload, headers=headers).status_code == 202
        pending = client.get("/v1/video/pending-notes", headers=headers)
        assert pending.status_code == 200
        assert len(pending.json()["items"]) == 1
        item = pending.json()["items"][0]

        updated = {**payload, "summary": "Обновлённая версия"}
        assert client.post("/v1/video/save-note", json=updated, headers=headers).status_code == 202
        latest = client.get("/v1/video/pending-notes", headers=headers).json()["items"][0]
        assert latest["revision"] != item["revision"]

        vault = tmp_path / "Mac Vault"
        (vault / "30_Knowledge").mkdir(parents=True)
        saved = save_video_note(**updated, vault_path=vault)
        wrong = client.post(
            f"/v1/video/pending-notes/{video_id}/complete",
            json={"revision": item["revision"], "relative_path": saved.relative_path,
                  "url": saved.url},
            headers=headers,
        )
        assert wrong.status_code == 409
        completed = client.post(
            f"/v1/video/pending-notes/{video_id}/complete",
            json={"revision": latest["revision"], "relative_path": saved.relative_path,
                  "url": saved.url}, headers=headers,
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "saved"
        assert client.get("/v1/video/pending-notes", headers=headers).json()["items"] == []


def test_pending_note_contents_require_configured_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VASYA_VIDEO_NOTE_QUEUE_MODE", "true")
    monkeypatch.setenv("VASYA_VIDEO_NOTE_QUEUE_FILE", str(tmp_path / "pending.db"))
    with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
        "apps.api.deps.VASYA_API_AUTH_TOKEN", None
    ), TestClient(app) as client:
        assert client.get("/v1/video/pending-notes").status_code == 503
        assert client.post("/v1/video/save-note", json={
            "video_id": "a" * 64, "summary": "Текст",
            "subtitle_srt": "1\n00:00:01,000 --> 00:00:02,000\nДа\n",
            "subtitle_origin": "original",
        }).status_code == 503
