"""Small, deterministic motion policy for the optional desktop companion walk."""

from __future__ import annotations

import random
import subprocess
import sys
from typing import Protocol


class ScreenRect(Protocol):
    def left(self) -> int: ...

    def right(self) -> int: ...

    def bottom(self) -> int: ...


def bottom_walk_lane(rect: ScreenRect, width: int, height: int) -> tuple[int, int, int]:
    left = rect.left() + 12
    right = max(left, rect.right() - width - 12)
    floor_y = rect.bottom() - height + 1
    return left, right, floor_y


def prefers_reduced_motion() -> bool:
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["/usr/bin/defaults", "read", "com.apple.universalaccess", "reduceMotion"],
            capture_output=True, text=True, timeout=1, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "1"


def visible_pack_state(
    assistant_state: str, ambient_state: str | None, default_state: str,
) -> str:
    if assistant_state == "idle" and ambient_state:
        return ambient_state
    return default_state


class AmbientWalker:
    """Choose rare short walks; callers decide when movement is permitted."""

    def __init__(self, *, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.next_walk_at: float | None = None
        self.direction = 0
        self.distance_left = 0
        self._suspended = False

    def stop(self, now: float) -> None:
        self.direction = 0
        self.distance_left = 0
        self.next_walk_at = now + self.rng.uniform(18.0, 40.0)

    def advance(
        self, now: float, x: int, left: int, right: int, *, allowed: bool,
    ) -> tuple[int, str | None]:
        if not allowed or right - left < 24:
            if not self._suspended:
                self.stop(now)
            self._suspended = True
            return x, None
        self._suspended = False
        if self.next_walk_at is None:
            self.stop(now)
            return x, None
        x = min(max(x, left), right)
        if self.direction == 0:
            if now < self.next_walk_at:
                return x, None
            possible = [direction for direction, room in ((-1, x - left), (1, right - x))
                        if room >= 24]
            if not possible:
                self.stop(now)
                return x, None
            self.direction = self.rng.choice(possible)
            room = x - left if self.direction < 0 else right - x
            self.distance_left = min(room, self.rng.randint(48, 120))

        direction = self.direction
        room = x - left if direction < 0 else right - x
        step = min(2, room, self.distance_left)
        x += direction * step
        self.distance_left -= step
        if step == 0 or self.distance_left <= 0:
            self.stop(now)
        return x, "walk_left" if direction < 0 else "walk_right"
