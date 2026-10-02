from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.main import app
from voice.models import TranscriptionResult


def test_voice_upload_transcribes_and_removes_temp_file() -> None:
    seen: list[Path] = []

    def fake_transcribe(path: str) -> TranscriptionResult:
        media = Path(path)
        seen.append(media)
        assert media.read_bytes() == b"voice-data"
        return TranscriptionResult("Статус проектов?", "ru", None, None)

    with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
        "apps.api.routes.voice._probe_audio_duration", return_value=5.0
    ), patch("apps.api.routes.voice.transcribe", side_effect=fake_transcribe):
        with TestClient(app) as client:
            response = client.post(
                "/v1/voice/transcribe", content=b"voice-data",
                headers={"x-voice-extension": "ogg"},
            )
    assert response.status_code == 200
    assert response.json() == {"text": "Статус проектов?", "language": "ru"}
    assert seen and not seen[0].exists()


def test_voice_upload_rejects_bad_extension_and_oversize() -> None:
    with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False):
        with TestClient(app) as client:
            invalid = client.post("/v1/voice/transcribe", content=b"a", headers={"x-voice-extension": "exe"})
            with patch("apps.api.routes.voice.MAX_VOICE_BYTES", 4):
                large = client.post("/v1/voice/transcribe", content=b"12345", headers={"x-voice-extension": "ogg"})
    assert invalid.status_code == 415
    assert large.status_code == 413


def test_voice_upload_requires_auth_and_rejects_long_audio() -> None:
    with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", True), patch(
        "apps.api.deps.VASYA_API_AUTH_TOKEN", "secret"
    ):
        with TestClient(app) as client:
            denied = client.post("/v1/voice/transcribe", content=b"voice", headers={"x-voice-extension": "ogg"})
            with patch("apps.api.routes.voice._probe_audio_duration", return_value=301.0):
                long_audio = client.post(
                    "/v1/voice/transcribe", content=b"voice",
                    headers={"x-voice-extension": "ogg", "x-api-key": "secret"},
                )
    assert denied.status_code == 401
    assert long_audio.status_code == 413
