from __future__ import annotations

import threading

from config.settings import HOTKEY_COMBINATION, HOTKEY_EXIT_COMBINATION
from utils.hotkeys import normalize_hotkey_combination
from utils.logger import log, log_voice_event
from voice.session import run_voice_interaction
from voice.tts import speak


def main() -> None:
    try:
        from pynput import keyboard
    except ImportError:
        print("pynput is not installed. Run: pip install -r requirements.txt")
        raise SystemExit(1)

    interaction_lock = threading.Lock()
    stop_event = threading.Event()

    def on_activate() -> None:
        if interaction_lock.locked():
            log_voice_event("hotkey_ignored reason=interaction_in_progress")
            return

        def worker() -> None:
            with interaction_lock:
                log_voice_event("hotkey_activated")
                run_voice_interaction()

        threading.Thread(target=worker, daemon=True).start()

    def on_exit() -> None:
        log("hotkey daemon exit requested")
        stop_event.set()
        listener.stop()

    activation_hotkey = normalize_hotkey_combination(HOTKEY_COMBINATION)
    exit_hotkey = normalize_hotkey_combination(HOTKEY_EXIT_COMBINATION)
    hotkeys = {
        activation_hotkey: on_activate,
        exit_hotkey: on_exit,
    }

    log(
        f"Starting hotkey daemon. Activation: {activation_hotkey}. "
        f"Exit: {exit_hotkey}."
    )
    speak("Vasya запущен в фоновом режиме.")

    try:
        listener = keyboard.GlobalHotKeys(hotkeys)
    except ValueError as exc:
        raise SystemExit(f"Invalid hotkey configuration: {exc}") from exc
    listener.start()
    stop_event.wait()


if __name__ == "__main__":
    main()
