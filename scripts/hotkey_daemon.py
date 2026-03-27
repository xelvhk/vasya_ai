from __future__ import annotations

import threading
import time

from assistant.control import AssistantControlAction
from assistant.state import AssistantStateName, assistant_state
from config.settings import (
    HOTKEY_COMBINATION,
    HOTKEY_EXIT_COMBINATION,
    INTERRUPT_LISTEN_DELAY_SECONDS,
)
from utils.hotkeys import normalize_hotkey_combination
from utils.logger import log, log_voice_event
from voice.session import run_voice_interaction
from voice.tts import speak, stop_speaking


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
            if assistant_state.get().name == AssistantStateName.SPEAKING:
                log_voice_event("hotkey_interrupt_speaking")
                stop_speaking()
                queue_followup_interaction()
                return
            else:
                log_voice_event("hotkey_ignored reason=interaction_in_progress")
                return

        start_interaction_thread("hotkey_activated")

    def queue_followup_interaction() -> None:
        def delayed_worker() -> None:
            with interaction_lock:
                pass
            time.sleep(INTERRUPT_LISTEN_DELAY_SECONDS)
            start_interaction_thread("hotkey_followup_activated")

        threading.Thread(target=delayed_worker, daemon=True).start()

    def start_interaction_thread(log_event: str) -> None:
        def worker() -> None:
            with interaction_lock:
                log_voice_event(log_event)
                action = run_voice_interaction()
                if action == AssistantControlAction.EXIT:
                    on_exit()

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
