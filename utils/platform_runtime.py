from __future__ import annotations

import platform
from typing import Literal


PlatformName = Literal["macos", "windows", "linux", "unknown"]


def get_platform_name() -> PlatformName:
    system_name = platform.system().lower()
    if system_name == "darwin":
        return "macos"
    if system_name == "windows":
        return "windows"
    if system_name == "linux":
        return "linux"
    return "unknown"
