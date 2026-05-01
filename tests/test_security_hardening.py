from __future__ import annotations

import json
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path

from services import integration_settings_service as integration_service
from services import secret_store
from utils import logger as app_logger


class _FakeWebSocket:
    def __init__(self, *, headers: dict[str, str] | None = None, query_params: dict[str, str] | None = None):
        self.headers = headers or {}
        self.query_params = query_params or {}


class ApiAuthPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api_deps, self.http_exception_type = _load_api_deps_module()
        self._orig_require_auth = self.api_deps.VASYA_API_REQUIRE_AUTH
        self._orig_token = self.api_deps.VASYA_API_AUTH_TOKEN
        self._orig_allow_query = self.api_deps.VASYA_API_ALLOW_QUERY_TOKEN

    def tearDown(self) -> None:
        self.api_deps.VASYA_API_REQUIRE_AUTH = self._orig_require_auth
        self.api_deps.VASYA_API_AUTH_TOKEN = self._orig_token
        self.api_deps.VASYA_API_ALLOW_QUERY_TOKEN = self._orig_allow_query

    def test_http_auth_accepts_bearer_token(self) -> None:
        self.api_deps.VASYA_API_REQUIRE_AUTH = True
        self.api_deps.VASYA_API_AUTH_TOKEN = "token123"
        self.api_deps.require_api_key(x_api_key=None, authorization="Bearer token123")

    def test_http_auth_rejects_when_token_missing(self) -> None:
        self.api_deps.VASYA_API_REQUIRE_AUTH = True
        self.api_deps.VASYA_API_AUTH_TOKEN = ""
        with self.assertRaises(self.http_exception_type) as ctx:
            self.api_deps.require_api_key(x_api_key="any", authorization=None)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_ws_query_token_disabled_by_default(self) -> None:
        self.api_deps.VASYA_API_REQUIRE_AUTH = True
        self.api_deps.VASYA_API_AUTH_TOKEN = "token123"
        self.api_deps.VASYA_API_ALLOW_QUERY_TOKEN = False
        ws = _FakeWebSocket(query_params={"api_key": "token123"})
        self.assertFalse(self.api_deps.is_ws_authorized(ws))

    def test_ws_query_token_can_be_enabled_explicitly(self) -> None:
        self.api_deps.VASYA_API_REQUIRE_AUTH = True
        self.api_deps.VASYA_API_AUTH_TOKEN = "token123"
        self.api_deps.VASYA_API_ALLOW_QUERY_TOKEN = True
        ws = _FakeWebSocket(query_params={"api_key": "token123"})
        self.assertTrue(self.api_deps.is_ws_authorized(ws))


class IntegrationSecretsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(self._tmp_dir.name)
        self._settings_file = tmp_path / "integrations.json"
        self._secrets_file = tmp_path / "integration_secrets.json"

        self._orig_settings_path = integration_service.INTEGRATIONS_STATE_FILE
        self._orig_secrets_path = secret_store.INTEGRATIONS_SECRETS_FILE
        self._orig_keyring_backend = secret_store._keyring_backend

        integration_service.INTEGRATIONS_STATE_FILE = str(self._settings_file)
        secret_store.INTEGRATIONS_SECRETS_FILE = str(self._secrets_file)
        secret_store._keyring_backend = lambda: None

    def tearDown(self) -> None:
        integration_service.INTEGRATIONS_STATE_FILE = self._orig_settings_path
        secret_store.INTEGRATIONS_SECRETS_FILE = self._orig_secrets_path
        secret_store._keyring_backend = self._orig_keyring_backend
        self._tmp_dir.cleanup()

    def test_sensitive_tokens_not_stored_in_main_settings_file(self) -> None:
        integration_service.save_integration_settings(
            {
                "github_default_repo": "owner/repo",
                "github_api_token": "ghp_123456789",
                "notion_api_token": "secret_notion_token",
            }
        )
        payload = json.loads(self._settings_file.read_text(encoding="utf-8"))
        self.assertIn("github_default_repo", payload)
        self.assertNotIn("github_api_token", payload)
        self.assertNotIn("notion_api_token", payload)

        self.assertEqual(integration_service.get_integration_setting("github_api_token"), "ghp_123456789")
        self.assertEqual(integration_service.get_integration_setting("notion_api_token"), "secret_notion_token")


class LoggerRedactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_redact = app_logger.LOG_REDACT_SENSITIVE
        self._orig_include_text = app_logger.LOG_INCLUDE_TEXT_CONTENT
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._orig_interaction_log = app_logger.INTERACTION_LOG_FILE

    def tearDown(self) -> None:
        app_logger.LOG_REDACT_SENSITIVE = self._orig_redact
        app_logger.LOG_INCLUDE_TEXT_CONTENT = self._orig_include_text
        app_logger.INTERACTION_LOG_FILE = self._orig_interaction_log
        self._tmp_dir.cleanup()

    def test_sanitize_payload_masks_text_and_token(self) -> None:
        app_logger.LOG_REDACT_SENSITIVE = True
        app_logger.LOG_INCLUDE_TEXT_CONTENT = False
        data = app_logger._sanitize_payload(
            {
                "user_text": "привет как дела",
                "api_token": "super-secret-token-value",
                "nested": {"authorization": "Bearer abcdef"},
            }
        )
        self.assertEqual(data["user_text"], "<redacted_text:15 chars>")
        self.assertEqual(data["api_token"], "<redacted_secret>")
        self.assertEqual(data["nested"]["authorization"], "<redacted_secret>")

    def test_log_interaction_event_writes_redacted_payload(self) -> None:
        app_logger.LOG_REDACT_SENSITIVE = True
        app_logger.LOG_INCLUDE_TEXT_CONTENT = False
        log_path = Path(self._tmp_dir.name) / "interactions.log"
        app_logger.INTERACTION_LOG_FILE = str(log_path)

        app_logger.log_interaction_event(
            "interaction",
            {
                "user_text": "секретная фраза",
                "api_token": "abcdef1234567890supersecret",
            },
        )

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertTrue(lines)
        payload = json.loads(lines[-1])
        self.assertEqual(payload["user_text"], "<redacted_text:15 chars>")
        self.assertEqual(payload["api_token"], "<redacted_secret>")
        self.assertIn("request_id", payload)
        self.assertIn("session_id", payload)


if __name__ == "__main__":
    unittest.main()


def _load_api_deps_module():
    fastapi_module = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    def Header(default=None):
        return default

    class WebSocket:
        pass

    fastapi_module.HTTPException = HTTPException
    fastapi_module.Header = Header
    fastapi_module.WebSocket = WebSocket

    sys.modules["fastapi"] = fastapi_module
    sys.modules.pop("config.settings", None)
    sys.modules.pop("apps.api.deps", None)
    api_deps = importlib.import_module("apps.api.deps")
    return api_deps, HTTPException
