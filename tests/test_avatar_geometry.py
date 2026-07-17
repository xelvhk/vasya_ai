from __future__ import annotations

import unittest
from dataclasses import dataclass

from scripts.ui.avatar_geometry import clamp_to_visible_area, snap_to_nearest_edge


@dataclass(frozen=True)
class FakePoint:
    x_value: int
    y_value: int

    def x(self) -> int:
        return self.x_value

    def y(self) -> int:
        return self.y_value


@dataclass(frozen=True)
class FakeRect:
    left_value: int
    right_value: int
    top_value: int
    bottom_value: int

    def left(self) -> int:
        return self.left_value

    def right(self) -> int:
        return self.right_value

    def top(self) -> int:
        return self.top_value

    def bottom(self) -> int:
        return self.bottom_value


class FakeScreen:
    def __init__(self, rect: FakeRect) -> None:
        self._rect = rect

    def availableGeometry(self) -> FakeRect:
        return self._rect


class FakeScreenProvider:
    _screens: list[FakeScreen] = []

    @staticmethod
    def primaryScreen() -> FakeScreen | None:
        return FakeScreenProvider._screens[0] if FakeScreenProvider._screens else None

    @staticmethod
    def screens() -> list[FakeScreen]:
        return list(FakeScreenProvider._screens)


class AvatarGeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeScreenProvider._screens = [FakeScreen(FakeRect(0, 1000, 0, 800))]

    def test_clamp_keeps_visible_position(self) -> None:
        position = FakePoint(200, 300)

        result = clamp_to_visible_area(
            position,
            120,
            160,
            screen_provider=FakeScreenProvider,
            point_factory=FakePoint,
        )

        self.assertIs(result, position)

    def test_clamp_moves_hidden_position_into_primary_screen(self) -> None:
        result = clamp_to_visible_area(
            FakePoint(-100, 900),
            120,
            160,
            screen_provider=FakeScreenProvider,
            point_factory=FakePoint,
        )

        self.assertEqual(result, FakePoint(24, 640))

    def test_snap_moves_to_nearest_edge_after_clamping(self) -> None:
        result = snap_to_nearest_edge(
            FakePoint(850, 120),
            120,
            160,
            screen_provider=FakeScreenProvider,
            point_factory=FakePoint,
        )

        self.assertEqual(result, FakePoint(864, 120))

    def test_snap_returns_position_when_no_primary_screen_exists(self) -> None:
        FakeScreenProvider._screens = []
        position = FakePoint(850, 120)

        result = snap_to_nearest_edge(
            position,
            120,
            160,
            screen_provider=FakeScreenProvider,
            point_factory=FakePoint,
        )

        self.assertIs(result, position)


if __name__ == "__main__":
    unittest.main()
