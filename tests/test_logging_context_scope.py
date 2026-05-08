from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import logger as app_logger


class LoggingContextScopeTests(unittest.TestCase):
    def test_start_logging_scope_reuses_session_and_rotates_request(self) -> None:
        req1, sess = app_logger.start_logging_scope()
        req2, sess2 = app_logger.start_logging_scope(session_id=sess)
        self.assertNotEqual(req1, req2)
        self.assertEqual(sess, sess2)

    def test_log_interaction_event_uses_current_scope_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "interactions.log"
            with patch.object(app_logger, "INTERACTION_LOG_FILE", str(log_file)):
                req, sess = app_logger.start_logging_scope()
                app_logger.log_interaction_event("test_event", {"step": "x"})
            row = json.loads(log_file.read_text(encoding="utf-8").strip())
            self.assertEqual(row.get("request_id"), req)
            self.assertEqual(row.get("session_id"), sess)


if __name__ == "__main__":
    unittest.main()
