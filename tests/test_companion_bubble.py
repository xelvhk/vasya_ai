"""Desktop bubble behavior without launching the assistant runtime."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from scripts.ui.companion_bubble import ResponseBubble
except ImportError:  # pragma: no cover - Linux CI may omit the Qt EGL runtime
    QApplication = None
    ResponseBubble = None


@unittest.skipUnless(ResponseBubble is not None, "Qt desktop runtime is unavailable")
class CompanionBubbleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.bubble = ResponseBubble()

    def tearDown(self) -> None:
        self.bubble.close()

    def test_submit_trims_text_and_keeps_full_answer(self) -> None:
        submitted: list[str] = []
        self.bubble.question_submitted.connect(submitted.append)
        answer = "Развёрнутый ответ. " * 20
        self.bubble.set_text(answer)
        self.assertEqual(self.bubble._answer.toPlainText(), answer)
        self.bubble._input.setText("  Что дальше?  ")
        self.bubble._submit()
        self.assertEqual(submitted, ["Что дальше?"])
        self.assertEqual(self.bubble._input.text(), "")

    def test_empty_question_is_not_sent_and_close_emits_dismissed(self) -> None:
        submitted: list[str] = []
        dismissed: list[bool] = []
        self.bubble.question_submitted.connect(submitted.append)
        self.bubble.dismissed.connect(lambda: dismissed.append(True))
        self.bubble._input.setText("   ")
        self.bubble._submit()
        self.assertEqual(submitted, [])
        self.bubble._dismiss()
        self.assertEqual(dismissed, [True])


if __name__ == "__main__":
    unittest.main()
