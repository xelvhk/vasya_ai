from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.main import app
from services.focus_radio_bridge import take_commands, write_status


class FocusRadioApiTests(unittest.TestCase):
    def test_offline_and_validated_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("apps.api.deps.VASYA_API_REQUIRE_AUTH", False), patch(
                "apps.api.routes.focus_radio.APP_PATHS"
            ) as paths:
                paths.data_dir = root
                with TestClient(app) as client:
                    self.assertEqual(client.get("/v1/focus-radio").json(), {"available": False})
                    self.assertEqual(client.post("/v1/focus-radio", json={"action": "play"}).status_code, 503)
                    write_status(root, {"playing": False, "mode": "warm", "volume": 0.32})
                    self.assertEqual(client.post("/v1/focus-radio", json={"action": "mode", "mode": "invalid"}).status_code, 422)
                    self.assertEqual(client.post("/v1/focus-radio", json={"action": "volume", "volume": 1.5}).status_code, 422)
                    self.assertEqual(client.post("/v1/focus-radio", json={"action": "mode", "mode": "rain"}).status_code, 202)
                    self.assertEqual(take_commands(root), [{"action": "mode", "mode": "rain"}])
