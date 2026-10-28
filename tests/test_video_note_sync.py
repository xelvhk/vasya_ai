import hashlib
import plistlib

import pytest

from fastapi.testclient import TestClient

from apps.api.main import app
from scripts import sync_video_notes
from scripts import video_note_sync_launchd


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


def test_api_key_file_requires_private_regular_file(tmp_path) -> None:
    key_file = tmp_path / "sync.key"
    key_file.write_text("private-token\n")
    key_file.chmod(0o600)
    assert sync_video_notes.read_api_key_file(key_file) == "private-token"

    key_file.chmod(0o644)
    with pytest.raises(ValueError, match="owner-only"):
        sync_video_notes.read_api_key_file(key_file)

    key_file.chmod(0o600)
    link = tmp_path / "link.key"
    link.symlink_to(key_file)
    with pytest.raises(ValueError, match="symbolic link"):
        sync_video_notes.read_api_key_file(link)


def test_launch_agent_runs_sync_periodically_without_embedding_key(tmp_path) -> None:
    vault = tmp_path / "Vault"
    key_file = tmp_path / "sync.key"
    payload = video_note_sync_launchd.build_launch_agent(
        server="https://vasya.example.test",
        vault=vault,
        api_key_file=key_file,
        python=tmp_path / "venv/bin/python",
        repo=tmp_path / "repo",
        logs=tmp_path / "logs",
        interval=300,
    )
    encoded = plistlib.dumps(payload)
    assert payload["StartInterval"] == 300
    assert payload["RunAtLoad"] is True
    assert payload["WorkingDirectory"] == str(tmp_path / "repo")
    assert payload["ProgramArguments"][-2:] == ["--api-key-file", str(key_file)]
    assert b"private-token" not in encoded


def test_launch_agent_rejects_insecure_server_and_fast_interval(tmp_path) -> None:
    options = dict(
        vault=tmp_path / "Vault", api_key_file=tmp_path / "sync.key",
        python=tmp_path / "python", repo=tmp_path / "repo", logs=tmp_path / "logs",
        interval=300,
    )
    with pytest.raises(ValueError, match="HTTPS"):
        video_note_sync_launchd.build_launch_agent(server="http://192.0.2.1", **options)
    with pytest.raises(ValueError, match="60"):
        video_note_sync_launchd.build_launch_agent(
            server="https://vasya.example.test", **{**options, "interval": 5}
        )


def test_launch_agent_install_uses_private_file_and_refuses_overwrite(tmp_path, monkeypatch) -> None:
    key_file = tmp_path / "sync.key"
    key_file.write_text("private-token\n")
    key_file.chmod(0o600)
    payload = video_note_sync_launchd.build_launch_agent(
        server="https://vasya.example.test", vault=tmp_path / "Vault",
        api_key_file=key_file, python=tmp_path / "python", repo=tmp_path / "repo",
        logs=tmp_path / "logs",
    )
    plist_path = tmp_path / "LaunchAgents" / "sync.plist"
    calls = []
    monkeypatch.setattr(
        video_note_sync_launchd.subprocess, "run", lambda *a, **k: calls.append((a, k))
    )

    video_note_sync_launchd.install_launch_agent(payload, plist_path, key_file)
    assert plistlib.loads(plist_path.read_bytes()) == payload
    assert plist_path.stat().st_mode & 0o077 == 0
    assert calls[0][0][0][:2] == ["launchctl", "bootstrap"]
    with pytest.raises(FileExistsError):
        video_note_sync_launchd.install_launch_agent(payload, plist_path, key_file)


def test_launch_agent_install_rejects_public_key_file(tmp_path) -> None:
    key_file = tmp_path / "sync.key"
    key_file.write_text("private-token")
    key_file.chmod(0o644)
    with pytest.raises(ValueError, match="owner-only"):
        video_note_sync_launchd.install_launch_agent({}, tmp_path / "sync.plist", key_file)
