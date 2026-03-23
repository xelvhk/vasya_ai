from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from assistant.state import AssistantState, AssistantStateName, assistant_state
from config.settings import AVATAR_IMAGE_PATH, AVATAR_SIZE, AVATAR_STATE_FILE
from utils.logger import log
from voice.session import run_voice_interaction


def main() -> None:
    try:
        from PySide6.QtCore import QObject, QPoint, QRectF, Qt, QTimer, Signal
        from PySide6.QtGui import QColor, QFont, QGuiApplication, QMouseEvent, QPainter, QPen, QPixmap
        from PySide6.QtWidgets import QApplication, QWidget
    except ImportError:
        print("PySide6 is not installed. Run: pip install -r requirements.txt")
        raise SystemExit(1)

    class StateBridge(QObject):
        state_changed = Signal(object)

    class ResponseBubble(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._text = ""
            self.resize(220, 72)

        def set_text(self, text: str) -> None:
            self._text = text
            self.update()

        def paintEvent(self, event) -> None:
            _ = event
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(10, 22, 62, 225))
            painter.setPen(QPen(QColor("#6ea9ff"), 1))
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 18, 18)

            painter.setPen(QColor("#f4f8ff"))
            painter.setFont(QFont("Helvetica", 10))
            painter.drawText(
                self.rect().adjusted(16, 12, -16, -12),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                self._text,
            )

    class AvatarWidget(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setFixedSize(AVATAR_SIZE, AVATAR_SIZE)

            self._drag_pos: QPoint | None = None
            self._press_pos: QPoint | None = None
            self._interaction_lock = threading.Lock()
            self._state = assistant_state.get()
            self._pulse = 0.0
            self._avatar = self._load_avatar()
            self._bridge = StateBridge()
            self._bubble = ResponseBubble()

            self._bridge.state_changed.connect(self._apply_state)
            assistant_state.subscribe(self._on_state_changed)

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(60)

            self._restore_position()
            self._update_bubble()

        def _load_avatar(self):
            if not AVATAR_IMAGE_PATH:
                return None
            path = Path(AVATAR_IMAGE_PATH)
            if not path.exists():
                return None
            pixmap = QPixmap(str(path))
            return pixmap if not pixmap.isNull() else None

        def _on_state_changed(self, state: AssistantState) -> None:
            self._bridge.state_changed.emit(state)

        def _apply_state(self, state: AssistantState) -> None:
            self._state = state
            self._update_bubble()
            self.update()

        def _tick(self) -> None:
            self._pulse = (self._pulse + 0.08) % 6.28
            self.update()
            self._update_bubble_position()

        def mousePressEvent(self, event: QMouseEvent) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                self._press_pos = event.globalPosition().toPoint()
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

        def mouseMoveEvent(self, event: QMouseEvent) -> None:
            if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                self._update_bubble_position()

        def mouseReleaseEvent(self, event: QMouseEvent) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                release_pos = event.globalPosition().toPoint()
                moved_distance = 0
                if self._press_pos is not None:
                    moved_distance = (release_pos - self._press_pos).manhattanLength()
                self._drag_pos = None
                self._press_pos = None
                if moved_distance <= 6:
                    self._activate_interaction()
                else:
                    self._save_position()

        def contextMenuEvent(self, event) -> None:
            _ = event
            self.close()

        def _activate_interaction(self) -> None:
            if self._interaction_lock.locked():
                return

            def worker() -> None:
                with self._interaction_lock:
                    run_voice_interaction()

            threading.Thread(target=worker, daemon=True).start()

        def closeEvent(self, event) -> None:
            self._save_position()
            self._bubble.close()
            super().closeEvent(event)

        def paintEvent(self, event) -> None:
            _ = event
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            glow_color = _glow_color(self._state.name)
            glow_alpha = 110 + int(40 * abs(__import__("math").sin(self._pulse)))
            glow = QColor(glow_color)
            glow.setAlpha(glow_alpha)
            painter.setBrush(glow)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(8, 8, self.width() - 16, self.height() - 16))

            if self._avatar:
                painter.drawPixmap(self.rect(), self._avatar)
            else:
                self._paint_fallback(painter)

        def _paint_fallback(self, painter: QPainter) -> None:
            rect = QRectF(18, 18, self.width() - 36, self.height() - 36)
            gradient_color = _glow_color(self._state.name)

            painter.setBrush(QColor("#102a72"))
            painter.setPen(QPen(QColor(gradient_color), 4))
            painter.drawEllipse(rect)

            inner = QRectF(32, 32, self.width() - 64, self.height() - 64)
            painter.setBrush(QColor("#f7f9ff"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(inner)

            painter.setBrush(QColor("#101a4d"))
            painter.drawEllipse(QRectF(44, 52, 20, 28))
            painter.drawEllipse(QRectF(76, 52, 20, 28))

            painter.setPen(QPen(QColor("#1c275f"), 4))
            painter.drawArc(QRectF(54, 76, 32, 18), 200 * 16, 140 * 16)

            painter.setPen(QColor("#d9e7ff"))
            painter.setFont(QFont("Helvetica", 8))
            painter.drawText(self.rect().adjusted(0, self.height() - 22, 0, -4), Qt.AlignmentFlag.AlignCenter, self._state.name.value)

        def _bubble_text(self) -> str:
            if self._state.message:
                return self._state.message.strip()
            if self._state.name == AssistantStateName.LISTENING:
                return "Слушаю..."
            if self._state.name == AssistantStateName.THINKING:
                return "Думаю..."
            if self._state.name == AssistantStateName.SPEAKING:
                return "Отвечаю..."
            if self._state.name == AssistantStateName.ERROR:
                return "Что-то пошло не так"
            return ""

        def _update_bubble(self) -> None:
            text = self._bubble_text()
            if not text or self._state.name == AssistantStateName.IDLE:
                self._bubble.hide()
                return

            if len(text) > 110:
                text = f"{text[:107]}..."
            self._bubble.set_text(text)
            self._update_bubble_position()
            self._bubble.show()
            self._bubble.raise_()

        def _update_bubble_position(self) -> None:
            if not self._bubble.isVisible():
                return

            bubble_x = self.x() + self.width() + 12
            bubble_y = self.y() + max(8, (self.height() - self._bubble.height()) // 2)
            self._bubble.move(bubble_x, bubble_y)

        def _restore_position(self) -> None:
            saved_pos = _load_saved_position()
            if saved_pos is not None:
                self.move(saved_pos)
                return

            screen = QGuiApplication.primaryScreen()
            if screen is None:
                self.move(100, 100)
                return

            available = screen.availableGeometry()
            default_x = max(24, available.right() - self.width() - 48)
            default_y = max(24, available.bottom() - self.height() - 120)
            self.move(default_x, default_y)

        def _save_position(self) -> None:
            _save_position(self.pos())

    def _glow_color(state_name: AssistantStateName) -> str:
        if state_name == AssistantStateName.LISTENING:
            return "#3ec8ff"
        if state_name == AssistantStateName.THINKING:
            return "#6fa8ff"
        if state_name == AssistantStateName.SPEAKING:
            return "#5b7cff"
        if state_name == AssistantStateName.ERROR:
            return "#ff6b6b"
        return "#4f8fff"

    def _load_saved_position() -> QPoint | None:
        state_path = Path(AVATAR_STATE_FILE)
        if not state_path.exists():
            return None
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        x = payload.get("x")
        y = payload.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return None
        return QPoint(x, y)

    def _save_position(position: QPoint) -> None:
        state_path = Path(AVATAR_STATE_FILE)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"x": int(position.x()), "y": int(position.y())}
        try:
            state_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError as exc:
            log(f"Failed to save avatar position: {exc}")

    app = QApplication(sys.argv)
    widget = AvatarWidget()
    widget.show()
    log("Avatar widget started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
