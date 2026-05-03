from __future__ import annotations

import unittest

from utils.intent_fastpaths import detect_fast_intent


class ObsidianIdeasTriageFastpathTests(unittest.TestCase):
    def test_triage_phrase_routes_to_obsidian_ideas_intent(self) -> None:
        intent = detect_fast_intent("разбери неразобранные идеи")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "triage_obsidian_ideas")
        self.assertEqual(intent.data, {})


if __name__ == "__main__":
    unittest.main()
