from __future__ import annotations

import random
import unittest
from unittest.mock import Mock, patch

from scripts.ui.avatar_ambient import (
    AmbientWalker, bottom_walk_lane, prefers_reduced_motion, visible_pack_state,
)


class FakeRect:
    def __init__(self, left: int, right: int, bottom: int) -> None:
        self._left = left
        self._right = right
        self._bottom = bottom

    def left(self) -> int:
        return self._left

    def right(self) -> int:
        return self._right

    def bottom(self) -> int:
        return self._bottom


class AmbientWalkerTests(unittest.TestCase):
    def test_lane_uses_the_supplied_monitor_bounds(self) -> None:
        self.assertEqual(
            bottom_walk_lane(FakeRect(1920, 3839, 1079), 96, 96),
            (1932, 3731, 984),
        )

    def test_walk_stays_bounded_then_pauses(self) -> None:
        walker = AmbientWalker(rng=random.Random(4))
        walker.next_walk_at = 0.0
        x = 50
        states = set()
        for tick in range(120):
            x, state = walker.advance(tick * 0.06, x, 10, 110, allowed=True)
            self.assertGreaterEqual(x, 10)
            self.assertLessEqual(x, 110)
            if state:
                states.add(state)
        self.assertTrue(states & {"walk_left", "walk_right"})
        self.assertGreater(walker.next_walk_at, 7.0)

    def test_user_interaction_stops_walk_immediately(self) -> None:
        walker = AmbientWalker(rng=random.Random(0))
        walker.next_walk_at = 0.0
        x, state = walker.advance(1.0, 50, 10, 110, allowed=True)
        self.assertIsNotNone(state)
        stopped_x, stopped_state = walker.advance(1.06, x, 10, 110, allowed=False)
        self.assertEqual(stopped_x, x)
        self.assertIsNone(stopped_state)
        self.assertEqual(walker.direction, 0)
        self.assertGreater(walker.next_walk_at, 1.06)

    def test_macos_reduced_motion_preference_disables_roaming(self) -> None:
        with patch("scripts.ui.avatar_ambient.sys.platform", "darwin"), patch(
            "scripts.ui.avatar_ambient.subprocess.run",
            return_value=Mock(returncode=0, stdout="1\n"),
        ):
            self.assertTrue(prefers_reduced_motion())

    def test_assistant_state_takes_priority_over_walk(self) -> None:
        self.assertEqual(visible_pack_state("thinking", "walk_left", "thinking"), "thinking")
        self.assertEqual(visible_pack_state("idle", "walk_left", "idle"), "walk_left")


if __name__ == "__main__":
    unittest.main()
