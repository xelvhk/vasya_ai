from __future__ import annotations

from assistant.child_mode import child_mode_store
from PySide6.QtCore import QRectF, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget


class AvatarPreview(QWidget):
    def __init__(self, widget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._widget = widget
        self._preview_size = widget._avatar_size
        self._preview_skin_id = widget._avatar_skin
        self._preview_child_mode_enabled = child_mode_store.is_enabled()
        self._preview_auto_child_skin = widget._auto_child_skin
        self._preview_opacity = widget._avatar_opacity
        self._idle_motion = widget._idle_motion_enabled
        self._pulse = 0.0
        self._bob = 0.0
        self.setFixedSize(150, 150)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def update_preview(
        self,
        *,
        size: int,
        skin_id: str,
        child_mode_enabled: bool,
        auto_child_skin: bool,
        opacity: float,
        idle_motion: bool,
    ) -> None:
        self._preview_size = size
        self._preview_skin_id = skin_id
        self._preview_child_mode_enabled = child_mode_enabled
        self._preview_auto_child_skin = auto_child_skin
        self._preview_opacity = opacity
        self._idle_motion = idle_motion
        self.update()

    def _tick(self) -> None:
        if self._idle_motion:
            self._pulse = (self._pulse + 0.05) % 6.28
            self._bob = (self._bob + 0.035) % 6.28
        else:
            self._pulse = 0.0
            self._bob = 0.0
        self.update()

    def _effective_skin_id(self) -> str:
        if self._preview_child_mode_enabled and self._preview_auto_child_skin:
            return "child"
        return self._preview_skin_id

    def _character_scale(self) -> float:
        return max(0.82, min(1.18, self._preview_size / 210.0))

    def paintEvent(self, event) -> None:
        _ = event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(max(0.45, min(1.0, self._preview_opacity)))
        preview_bounds = QRectF(10, 10, self.width() - 20, self.height() - 20)
        effective_skin = self._effective_skin_id()
        if self._widget._avatar:
            self._widget._paint_preview_image_avatar(
                painter,
                preview_bounds,
                pulse=self._pulse,
                bob=self._bob,
                skin_id=effective_skin,
            )
        else:
            self._widget._paint_preview_character(
                painter,
                preview_bounds,
                pulse=self._pulse,
                bob=self._bob,
                scale=self._character_scale(),
                skin_id=effective_skin,
                smile_bounce=0.0,
            )
