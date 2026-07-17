from __future__ import annotations

from typing import Protocol


class PointLike(Protocol):
    def x(self) -> int: ...

    def y(self) -> int: ...


class RectLike(Protocol):
    def left(self) -> int: ...

    def right(self) -> int: ...

    def top(self) -> int: ...

    def bottom(self) -> int: ...


class ScreenLike(Protocol):
    def availableGeometry(self) -> RectLike: ...


class ScreenProvider(Protocol):
    @staticmethod
    def primaryScreen() -> ScreenLike | None: ...

    @staticmethod
    def screens() -> list[ScreenLike]: ...


def clamp_to_visible_area(
    position: PointLike,
    width: int,
    height: int,
    *,
    screen_provider: ScreenProvider,
    point_factory,
):
    for screen in screen_provider.screens():
        available = screen.availableGeometry()
        max_x = available.right() - width
        max_y = available.bottom() - height
        if (
            available.left() <= position.x() <= max_x
            and available.top() <= position.y() <= max_y
        ):
            return position

    primary = screen_provider.primaryScreen()
    if primary is None:
        return point_factory(100, 100)

    available = primary.availableGeometry()
    clamped_x = min(max(position.x(), available.left() + 24), available.right() - width)
    clamped_y = min(max(position.y(), available.top() + 24), available.bottom() - height)
    return point_factory(clamped_x, clamped_y)


def snap_to_nearest_edge(
    position: PointLike,
    width: int,
    height: int,
    *,
    screen_provider: ScreenProvider,
    point_factory,
):
    primary = screen_provider.primaryScreen()
    if primary is None:
        return position

    available = primary.availableGeometry()
    clamped = clamp_to_visible_area(
        position,
        width,
        height,
        screen_provider=screen_provider,
        point_factory=point_factory,
    )
    left_x = available.left() + 16
    right_x = available.right() - width - 16
    target_x = left_x if abs(clamped.x() - left_x) <= abs(clamped.x() - right_x) else right_x
    return point_factory(target_x, clamped.y())
