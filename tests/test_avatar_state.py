from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ui.avatar_state import (
    load_saved_position,
    load_widget_state,
    save_widget_state,
    widget_visible_on_start,
)


class AvatarStateTests(unittest.TestCase):
    def test_load_widget_state_returns_empty_dict_when_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "missing" / "state.json"

            self.assertEqual(load_widget_state(state_path), {})

    def test_load_widget_state_ignores_invalid_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "state.json"
            state_path.write_text("[1, 2, 3]", encoding="utf-8")

            self.assertEqual(load_widget_state(state_path), {})

            state_path.write_text("{not-json", encoding="utf-8")
            self.assertEqual(load_widget_state(state_path), {})

    def test_load_saved_position_requires_integer_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "state.json"
            state_path.write_text(json.dumps({"x": 12, "y": 34}), encoding="utf-8")

            self.assertEqual(load_saved_position(state_path), (12, 34))

            state_path.write_text(json.dumps({"x": "12", "y": 34}), encoding="utf-8")
            self.assertIsNone(load_saved_position(state_path))

    def test_widget_visible_on_start_inverts_start_hidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "state.json"
            state_path.write_text(json.dumps({"start_hidden": True}), encoding="utf-8")

            self.assertFalse(widget_visible_on_start(state_path))

            state_path.write_text(json.dumps({"start_hidden": False}), encoding="utf-8")
            self.assertTrue(widget_visible_on_start(state_path))

    def test_save_widget_state_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "nested" / "state.json"

            self.assertTrue(save_widget_state(state_path, {"x": 1, "y": 2}))

            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")), {"x": 1, "y": 2})


if __name__ == "__main__":
    unittest.main()
