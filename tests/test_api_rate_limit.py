from __future__ import annotations

import unittest

from apps.api import rate_limit


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _Client:
    def __init__(self, host: str):
        self.host = host


class _Req:
    def __init__(self, host: str = "127.0.0.1", xff: str = ""):
        self.client = _Client(host)
        self.headers = _Headers({"x-forwarded-for": xff} if xff else {})


class RateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        rate_limit._HTTP_BUCKETS.clear()
        rate_limit._WS_MESSAGE_BUCKETS.clear()
        rate_limit._WS_CONNECTION_COUNTS.clear()

    def test_client_id_prefers_x_forwarded_for(self) -> None:
        req = _Req(host="10.1.1.1", xff="1.2.3.4, 5.6.7.8")
        self.assertEqual(rate_limit.resolve_client_id_from_request(req), "1.2.3.4")

    def test_http_rate_limit_blocks_after_limit(self) -> None:
        path = "/v1/chat"
        client_id = "client-1"
        now = 10_000.0

        for index in range(rate_limit.API_RATE_LIMIT_CHAT_MAX):
            decision = rate_limit.check_http_rate_limit(path, client_id, now=now + index * 0.01)
            self.assertTrue(decision.allowed)

        blocked = rate_limit.check_http_rate_limit(path, client_id, now=now + 0.5)
        self.assertFalse(blocked.allowed)
        self.assertGreaterEqual(blocked.retry_after_seconds, 1)

    def test_http_rate_limit_recovers_after_window(self) -> None:
        path = "/v1/pipeline"
        client_id = "client-2"
        now = 20_000.0

        for index in range(rate_limit.API_RATE_LIMIT_PIPELINE_MAX):
            decision = rate_limit.check_http_rate_limit(path, client_id, now=now + index * 0.01)
            self.assertTrue(decision.allowed)

        blocked = rate_limit.check_http_rate_limit(path, client_id, now=now + 0.3)
        self.assertFalse(blocked.allowed)

        after_window = now + float(rate_limit.API_RATE_LIMIT_WINDOW_SECONDS) + 1.0
        recovered = rate_limit.check_http_rate_limit(path, client_id, now=after_window)
        self.assertTrue(recovered.allowed)

    def test_ws_connection_limit(self) -> None:
        client_id = "ws-client"
        for _ in range(rate_limit.API_RATE_LIMIT_WS_CONNECTIONS_MAX):
            decision = rate_limit.register_ws_connection(client_id)
            self.assertTrue(decision.allowed)

        blocked = rate_limit.register_ws_connection(client_id)
        self.assertFalse(blocked.allowed)

        rate_limit.unregister_ws_connection(client_id)
        allowed_again = rate_limit.register_ws_connection(client_id)
        self.assertTrue(allowed_again.allowed)

    def test_ws_message_rate_limit(self) -> None:
        client_id = "ws-msg-client"
        now = 30_000.0
        for index in range(rate_limit.API_RATE_LIMIT_WS_MESSAGES_MAX):
            decision = rate_limit.check_ws_message_rate_limit(client_id, now=now + index * 0.01)
            self.assertTrue(decision.allowed)

        blocked = rate_limit.check_ws_message_rate_limit(client_id, now=now + 0.5)
        self.assertFalse(blocked.allowed)
        self.assertGreaterEqual(blocked.retry_after_seconds, 1)


if __name__ == "__main__":
    unittest.main()
