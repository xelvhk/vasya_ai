"""One desktop-owned focus radio player shared by the widget and tray."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


MODES = ("warm", "rain", "night", "pulse", "mix")
MIX_ORDER = MODES[:-1]
TRACKS = {
    "warm": ("focus-warm.wav",),
    "rain": ("focus-rain-soft.mp3", "focus-rain-deep.mp3"),
    "night": ("focus-night.mp3",),
    "pulse": ("focus-pulse.mp3",),
}


class FocusRadio:
    def __init__(self, owner, *, mode: str = "warm", volume: float = 0.32,
                 on_change: Callable[[], None] | None = None) -> None:
        self.mode = mode if mode in MODES else "warm"
        try:
            self.volume = min(1.0, max(0.0, float(volume)))
        except (TypeError, ValueError):
            self.volume = 0.32
        self.playing = False
        self._paused_for_mic = False
        self._ducked = False
        self._mix_index = 0
        self._on_change = on_change or (lambda: None)
        self._audio = QAudioOutput(owner)
        self._player = QMediaPlayer(owner)
        self._player.setAudioOutput(self._audio)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_error)
        self._mix_timer = QTimer(owner)
        self._mix_timer.setSingleShot(True)
        self._mix_timer.timeout.connect(self._advance_mix)
        self._apply_volume()

    def snapshot(self) -> dict:
        return {"mode": self.mode, "playing": self.playing,
                "volume": self.volume, "scene": self._scene(),
                "interrupted": self._paused_for_mic}

    def toggle(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        if self.playing:
            return
        self.playing = True
        if not self._paused_for_mic:
            if self._player.source().isEmpty():
                self._start_scene()
            else:
                self._player.play()
                self._start_mix_timer()
        self._on_change()

    def pause(self) -> None:
        if not self.playing:
            return
        self.playing = False
        self._player.pause()
        self._mix_timer.stop()
        self._on_change()

    def set_mode(self, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"Unknown focus radio mode: {mode}")
        self.mode = mode
        self._mix_index = 0
        if self.playing and not self._paused_for_mic:
            self._start_scene()
        else:
            self._player.stop()
            self._player.setSource(QUrl())
        self._on_change()

    def set_volume(self, volume: float) -> None:
        self.volume = min(1.0, max(0.0, float(volume)))
        self._apply_volume()
        self._on_change()

    def set_assistant_state(self, name: str) -> None:
        paused_for_mic = name == "listening"
        ducked = name == "speaking"
        if paused_for_mic != self._paused_for_mic:
            self._paused_for_mic = paused_for_mic
            if paused_for_mic:
                self._player.pause()
                self._mix_timer.stop()
            elif self.playing:
                self._start_scene()
        self._ducked = ducked
        self._apply_volume()
        self._on_change()

    def _scene(self) -> str:
        return MIX_ORDER[self._mix_index] if self.mode == "mix" else self.mode

    def _start_scene(self) -> None:
        self._mix_timer.stop()
        scene = self._scene()
        filename = random.choice(TRACKS[scene])
        path = Path(__file__).resolve().parents[2] / "assets" / "focus" / filename
        if not path.is_file():
            self.playing = False
            self._on_change()
            raise FileNotFoundError(path)
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._player.play()
        self._start_mix_timer()

    def _start_mix_timer(self) -> None:
        if self.mode == "mix" and self._scene() == "warm" and self.playing:
            self._mix_timer.start(180_000)

    def _advance_mix(self) -> None:
        if self.mode != "mix" or not self.playing:
            return
        self._mix_index = (self._mix_index + 1) % len(MIX_ORDER)
        self._start_scene()
        self._on_change()

    def _on_media_status(self, status) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia or not self.playing:
            return
        if self.mode == "mix":
            if self._scene() == "warm":
                self._player.setPosition(0)
                self._player.play()
            else:
                self._advance_mix()
        else:
            self._start_scene()

    def _on_error(self, _error, message: str) -> None:
        self.playing = False
        self._mix_timer.stop()
        self._on_change()
        print(f"Focus radio playback error: {message}")

    def _apply_volume(self) -> None:
        self._audio.setVolume(self.volume * (0.18 if self._ducked else 1.0))
