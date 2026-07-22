from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from assistant.state import AssistantStateName
from scripts.ui.avatar_assets import (
    avatar_state_key,
    cached_avatar_pack_result,
    load_avatar_pack_manifest,
    pack_frames_for_state,
    resolve_avatar_path,
)


class FakePixmap:
    def __init__(self, path: str) -> None:
        self.path = path

    def isNull(self) -> bool:
        return Path(self.path).name.startswith("missing")


class AvatarAssetsTests(unittest.TestCase):
    def test_avatar_state_key_maps_assistant_states_to_pack_states(self) -> None:
        self.assertEqual(avatar_state_key(AssistantStateName.LISTENING), "listening")
        self.assertEqual(avatar_state_key(AssistantStateName.THINKING), "thinking")
        self.assertEqual(avatar_state_key(AssistantStateName.SPEAKING), "speaking")
        self.assertEqual(avatar_state_key(AssistantStateName.ERROR), "error")
        self.assertEqual(avatar_state_key(AssistantStateName.IDLE), "idle")

    def test_resolve_avatar_path_prefers_existing_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            configured = Path(tmp) / "configured.png"
            override = Path(tmp) / "override.png"
            configured.write_text("configured", encoding="utf-8")
            override.write_text("override", encoding="utf-8")

            result = resolve_avatar_path(
                {"avatar_image_path": str(override)},
                str(configured),
            )

            self.assertEqual(result, override)

    def test_resolve_avatar_path_falls_back_to_existing_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            configured = Path(tmp) / "configured.png"
            configured.write_text("configured", encoding="utf-8")

            result = resolve_avatar_path(
                {"avatar_image_path": str(Path(tmp) / "missing.png")},
                str(configured),
            )

            self.assertEqual(result, configured)

    def test_load_avatar_pack_manifest_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text("{not json", encoding="utf-8")

            result = load_avatar_pack_manifest(manifest, FakePixmap)

            self.assertFalse(result.loaded)
            self.assertEqual(result.frames, {})

    def test_load_avatar_pack_manifest_skips_missing_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "states": {
                            "idle": ["idle_01.webp", "missing_idle.webp"],
                            "speaking": ["speaking_01.webp"],
                            "unknown": ["ignored.webp"],
                        },
                        "timing_ms": {"idle": 5, "speaking": 2500},
                    }
                ),
                encoding="utf-8",
            )

            result = load_avatar_pack_manifest(manifest, FakePixmap)

            self.assertTrue(result.loaded)
            self.assertEqual([Path(frame.path).name for frame in result.frames["idle"]], ["idle_01.webp"])
            self.assertEqual([Path(frame.path).name for frame in result.frames["speaking"]], ["speaking_01.webp"])
            self.assertNotIn("unknown", result.frames)
            self.assertEqual(result.timing_ms["idle"], 40)
            self.assertEqual(result.timing_ms["speaking"], 2000)
            self.assertEqual(result.frame_index, {"idle": 0, "speaking": 0})

    def test_cached_avatar_pack_result_restores_valid_payload(self) -> None:
        payload = {
            "frames": {"idle": [object()], "empty": []},
            "timing_ms": {"idle": 260},
        }

        result = cached_avatar_pack_result(payload)

        self.assertIsNotNone(result)
        self.assertEqual(set(result.frames), {"idle"})
        self.assertEqual(result.frame_index, {"idle": 0})

    def test_pack_frames_for_state_falls_back_to_idle(self) -> None:
        idle_frame = object()
        self.assertEqual(
            pack_frames_for_state({"idle": [idle_frame]}, "speaking"),
            [idle_frame],
        )
        self.assertEqual(pack_frames_for_state({}, "speaking"), [])


if __name__ == "__main__":
    unittest.main()
