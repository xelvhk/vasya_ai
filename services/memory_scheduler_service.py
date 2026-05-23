from __future__ import annotations

import threading
import time
from collections.abc import Callable

from config.settings import (
    MEMORY_BACKGROUND_SYNC_ENABLED,
    MEMORY_BACKGROUND_SYNC_TICK_SECONDS,
)
from services.memory_sync_service import sync_memory_source
from utils.logger import log


class MemoryBackgroundScheduler:
    _global_instance: "MemoryBackgroundScheduler | None" = None
    _global_lock = threading.Lock()

    def __init__(
        self,
        *,
        tick_seconds: int | None = None,
        sync_fn: Callable[..., dict] = sync_memory_source,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.tick_seconds = max(60, int(tick_seconds or MEMORY_BACKGROUND_SYNC_TICK_SECONDS))
        self._sync_fn = sync_fn
        self._sleep_fn = sleep_fn
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.last_result: dict | None = None

    @classmethod
    def start_global(cls) -> "MemoryBackgroundScheduler | None":
        if not MEMORY_BACKGROUND_SYNC_ENABLED:
            return None
        with cls._global_lock:
            if cls._global_instance is None:
                cls._global_instance = cls()
                cls._global_instance.start()
            return cls._global_instance

    def start(self) -> bool:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="vasya-memory-background-sync",
                daemon=True,
            )
            self._thread.start()
            return True

    def stop(self) -> None:
        self._stop_event.set()

    def run_once(self) -> dict:
        result = self._sync_fn("all", force=False)
        self.last_result = result
        return result

    def _run_loop(self) -> None:
        log("Memory Center background sync started.")
        while not self._stop_event.is_set():
            try:
                result = self.run_once()
                ingested = int(result.get("ingested", 0)) if isinstance(result, dict) else 0
                log(f"Memory Center background sync finished: ingested={ingested}")
            except Exception as exc:
                log(f"Memory Center background sync failed: {type(exc).__name__}: {exc}")
            self._sleep_until_next_tick()

    def _sleep_until_next_tick(self) -> None:
        remaining = float(self.tick_seconds)
        while remaining > 0 and not self._stop_event.is_set():
            step = min(remaining, 5.0)
            self._sleep_fn(step)
            remaining -= step


def start_memory_background_scheduler() -> MemoryBackgroundScheduler | None:
    return MemoryBackgroundScheduler.start_global()
