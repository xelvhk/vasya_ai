from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from services.memory_scheduler_service import MemoryBackgroundScheduler


class MemorySchedulerServiceTests(unittest.TestCase):
    def test_run_once_uses_non_forced_all_source_sync(self) -> None:
        sync_fn = Mock(return_value={"ok": True, "source": "all", "ingested": 3})
        scheduler = MemoryBackgroundScheduler(sync_fn=sync_fn, sleep_fn=lambda _seconds: None)

        result = scheduler.run_once()

        self.assertTrue(result["ok"])
        sync_fn.assert_called_once_with("all", force=False)

    def test_start_global_scheduler_is_idempotent(self) -> None:
        with patch("services.memory_scheduler_service.MEMORY_BACKGROUND_SYNC_ENABLED", True), patch.object(
            MemoryBackgroundScheduler,
            "start",
            return_value=True,
        ) as start:
            first = MemoryBackgroundScheduler.start_global()
            second = MemoryBackgroundScheduler.start_global()

        self.assertIs(first, second)
        start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
