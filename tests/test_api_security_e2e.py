from __future__ import annotations

import types
import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    from apps.api import deps as api_deps
    from apps.api import main as api_main
    from apps.api import rate_limit
    _FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    _FASTAPI_AVAILABLE = False


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi is not installed in the current virtual environment")
class ApiSecurityE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_require_auth = api_deps.VASYA_API_REQUIRE_AUTH
        self._orig_token = api_deps.VASYA_API_AUTH_TOKEN
        self._orig_allow_query = api_deps.VASYA_API_ALLOW_QUERY_TOKEN

        self._orig_rl_enabled = rate_limit.API_RATE_LIMIT_ENABLED
        self._orig_rl_window = rate_limit.API_RATE_LIMIT_WINDOW_SECONDS
        self._orig_rl_chat = rate_limit.API_RATE_LIMIT_CHAT_MAX
        self._orig_rl_pipeline = rate_limit.API_RATE_LIMIT_PIPELINE_MAX
        self._orig_rl_ws_messages = rate_limit.API_RATE_LIMIT_WS_MESSAGES_MAX
        self._orig_rl_ws_connections = rate_limit.API_RATE_LIMIT_WS_CONNECTIONS_MAX

        rate_limit._HTTP_BUCKETS.clear()
        rate_limit._WS_MESSAGE_BUCKETS.clear()
        rate_limit._WS_CONNECTION_COUNTS.clear()

    def tearDown(self) -> None:
        api_deps.VASYA_API_REQUIRE_AUTH = self._orig_require_auth
        api_deps.VASYA_API_AUTH_TOKEN = self._orig_token
        api_deps.VASYA_API_ALLOW_QUERY_TOKEN = self._orig_allow_query

        rate_limit.API_RATE_LIMIT_ENABLED = self._orig_rl_enabled
        rate_limit.API_RATE_LIMIT_WINDOW_SECONDS = self._orig_rl_window
        rate_limit.API_RATE_LIMIT_CHAT_MAX = self._orig_rl_chat
        rate_limit.API_RATE_LIMIT_PIPELINE_MAX = self._orig_rl_pipeline
        rate_limit.API_RATE_LIMIT_WS_MESSAGES_MAX = self._orig_rl_ws_messages
        rate_limit.API_RATE_LIMIT_WS_CONNECTIONS_MAX = self._orig_rl_ws_connections

        rate_limit._HTTP_BUCKETS.clear()
        rate_limit._WS_MESSAGE_BUCKETS.clear()
        rate_limit._WS_CONNECTION_COUNTS.clear()

    def test_http_chat_requires_token_when_auth_is_enabled(self) -> None:
        api_deps.VASYA_API_REQUIRE_AUTH = True
        api_deps.VASYA_API_AUTH_TOKEN = ""
        rate_limit.API_RATE_LIMIT_ENABLED = False

        with TestClient(api_main.app) as client:
            response = client.post("/v1/chat", json={"text": "привет"})
        self.assertEqual(response.status_code, 503)

    def test_http_chat_allows_valid_token(self) -> None:
        api_deps.VASYA_API_REQUIRE_AUTH = True
        api_deps.VASYA_API_AUTH_TOKEN = "token123"
        rate_limit.API_RATE_LIMIT_ENABLED = False

        fake_result = types.SimpleNamespace(intent="chat", response="ok", needs_followup=False)
        with patch("apps.api.routes.chat.process_text_detailed", return_value=fake_result):
            with TestClient(api_main.app) as client:
                response = client.post(
                    "/v1/chat",
                    json={"text": "привет"},
                    headers={"x-api-key": "token123"},
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "ok")

    def test_http_chat_rate_limit_returns_429(self) -> None:
        api_deps.VASYA_API_REQUIRE_AUTH = True
        api_deps.VASYA_API_AUTH_TOKEN = "token123"
        rate_limit.API_RATE_LIMIT_ENABLED = True
        rate_limit.API_RATE_LIMIT_WINDOW_SECONDS = 60
        rate_limit.API_RATE_LIMIT_CHAT_MAX = 2

        fake_result = types.SimpleNamespace(intent="chat", response="ok", needs_followup=False)
        with patch("apps.api.routes.chat.process_text_detailed", return_value=fake_result):
            with TestClient(api_main.app) as client:
                headers = {"x-api-key": "token123"}
                r1 = client.post("/v1/chat", json={"text": "раз"}, headers=headers)
                r2 = client.post("/v1/chat", json={"text": "два"}, headers=headers)
                r3 = client.post("/v1/chat", json={"text": "три"}, headers=headers)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r3.status_code, 429)
        self.assertIn("Retry-After", r3.headers)

    def test_ws_query_token_rejected_when_disabled(self) -> None:
        api_deps.VASYA_API_REQUIRE_AUTH = True
        api_deps.VASYA_API_AUTH_TOKEN = "token123"
        api_deps.VASYA_API_ALLOW_QUERY_TOKEN = False
        rate_limit.API_RATE_LIMIT_ENABLED = False

        with TestClient(api_main.app) as client:
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect("/v1/ws/voice?api_key=token123"):
                    pass

    def test_ws_message_rate_limit_closes_socket(self) -> None:
        api_deps.VASYA_API_REQUIRE_AUTH = True
        api_deps.VASYA_API_AUTH_TOKEN = "token123"
        api_deps.VASYA_API_ALLOW_QUERY_TOKEN = False
        rate_limit.API_RATE_LIMIT_ENABLED = True
        rate_limit.API_RATE_LIMIT_WINDOW_SECONDS = 60
        rate_limit.API_RATE_LIMIT_WS_MESSAGES_MAX = 1
        rate_limit.API_RATE_LIMIT_WS_CONNECTIONS_MAX = 3

        with TestClient(api_main.app) as client:
            with client.websocket_connect("/v1/ws/voice", headers={"x-api-key": "token123"}) as ws:
                ready = ws.receive_json()
                self.assertEqual(ready.get("type"), "ready")
                ws.send_json({"type": "ping"})
                pong = ws.receive_json()
                self.assertEqual(pong.get("type"), "pong")

                ws.send_json({"type": "ping"})
                error = ws.receive_json()
                self.assertEqual(error.get("type"), "error")
                self.assertIn("Rate limit exceeded", str(error.get("message")))
                with self.assertRaises(WebSocketDisconnect):
                    ws.receive_json()


if __name__ == "__main__":
    unittest.main()
