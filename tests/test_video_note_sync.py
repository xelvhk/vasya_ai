import hashlib

from fastapi.testclient import TestClient

from apps.api.main import app
from scripts import sync_video_notes


def test_mac_pulls_and_confirms_video_note(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VASYA_VIDEO_NOTE_QUEUE_MODE", "true")
    monkeypatch.setenv("VASYA_VIDEO_NOTE_QUEUE_FILE", str(tmp_path / "pending.db"))
    vault = tmp_path / "Mac Vault"
    (vault / "30_Knowledge").mkdir(parents=True)
    payload = {
        "video_id": hashlib.sha256(b"movie").hexdigest(), "source_url": None,
        "summary": "О проекте", "subtitle_srt": "1\n00:00:01,000 --> 00:00:02,000\nПривет\n",
        "subtitle_origin": "transcribed",
    }
    auth_dependencies = {
        dependency.call
        for route in app.routes if route.path.startswith("/v1/video/")
        for dependency in getattr(getattr(route, "dependant", None), "dependencies", ())
        if dependency.call.__name__ in {"require_api_key", "require_video_note_sync_key"}
    }
    save_endpoint = next(route.endpoint for route in app.routes if route.path == "/v1/video/save-note")
    sync_auth = save_endpoint.__globals__["require_video_note_sync_key"]
    monkeypatch.setitem(sync_auth.__globals__, "VASYA_API_AUTH_TOKEN", "secret")
    for dependency in auth_dependencies:
        app.dependency_overrides[dependency] = lambda: None
    try:
        client = TestClient(app)
        assert client.post(
            "/v1/video/save-note", json=payload, headers={"X-API-Key": "secret"}
        ).status_code == 202

        def local_request(url: str, api_key: str, body: dict | None = None) -> dict:
            path = url.removeprefix("http://127.0.0.1:8765")
            headers = {"X-API-Key": api_key}
            response = client.post(path, json=body, headers=headers) if body else client.get(
                path, headers=headers
            )
            response.raise_for_status()
            return response.json()

        monkeypatch.setattr(sync_video_notes, "_request_json", local_request)
        assert sync_video_notes.sync_once("http://127.0.0.1:8765", "secret", vault) == (1, 0)
        assert sync_video_notes.sync_once("http://127.0.0.1:8765", "secret", vault) == (0, 0)
    finally:
        for dependency in auth_dependencies:
            app.dependency_overrides.pop(dependency, None)
    assert len(list((vault / "30_Knowledge/Video").glob("*.md"))) == 1


def test_mac_sync_rejects_remote_plain_http(tmp_path) -> None:
    try:
        sync_video_notes.sync_once("http://192.0.2.1:8765", "secret", tmp_path)
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("private transcript could use remote plaintext HTTP")
