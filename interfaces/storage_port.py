from __future__ import annotations

from typing import Protocol


class StoragePort(Protocol):
    def get_state(self, key: str, default=None): ...

    def set_state(self, key: str, value) -> None: ...

    def delete_state(self, key: str) -> bool: ...
