from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from services.focus_radio_bridge import enqueue_command, read_status, take_commands, write_status


class FocusRadioBridgeTests(unittest.TestCase):
    def test_commands_are_ordered_and_consumed_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            enqueue_command(root, {"action": "mode", "mode": "rain"})
            enqueue_command(root, {"action": "play"})
            self.assertEqual([item["action"] for item in take_commands(root)], ["mode", "play"])
            self.assertEqual(take_commands(root), [])

    def test_stale_widget_status_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(read_status(root), {"available": False})
            write_status(root, {"playing": False, "mode": "warm", "volume": 0.32})
            self.assertTrue(read_status(root)["available"])
            self.assertEqual(read_status(root, now=time.time() + 10), {"available": False})
