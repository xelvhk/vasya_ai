from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from assistant.state import AssistantState, AssistantStateName, assistant_state
from config.settings import (
    AVATAR_IMAGE_PATH,
    AVATAR_SIZE,
    AVATAR_STATE_FILE,
    HOTKEY_COMBINATION,
    HOTKEY_EXIT_COMBINATION,
)
from utils.hotkeys import normalize_hotkey_combination
from utils.logger import log, log_voice_event
from voice.session import run_voice_interaction


def main() -> None:
    try:
        from PySide6.QtCore import QObject, QPoint, QRectF, Qt, QTimer, Signal
        from PySide6.QtGui import (
            QAction,
            QColor,
            QFont,
            QGuiApplication,
            QIcon,
            QMouseEvent,
            QPainter,
            QPen,
            QPixmap,
        )
        from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget
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
            self._tray_icon_pixmap = self._build_tray_pixmap()
            self._bridge = StateBridge()
            self._bubble = ResponseBubble()
            self._hotkey_listener = None
            self._tray = None
            self._allow_close = False

            self._bridge.state_changed.connect(self._apply_state)
            assistant_state.subscribe(self._on_state_changed)

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(60)

            self._restore_position()
            self._update_bubble()
            self._start_hotkey_listener()
            self._setup_tray()

        def _load_avatar(self):
            if not AVATAR_IMAGE_PATH:
                return None
            path = Path(AVATAR_IMAGE_PATH)
            if not path.exists():
                return None
            pixmap = QPixmap(str(path))
            return pixmap if not pixmap.isNull() else None

        def _build_tray_pixmap(self) -> QPixmap:
            if self._avatar:
                return self._avatar.scaled(
                    32,
                    32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#1d4ed8"))
            painter.setPen(QPen(QColor("#8fd0ff"), 2))
            painter.drawEllipse(QRectF(3, 3, 26, 26))
            painter.setBrush(QColor("#f7f9ff"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(8, 8, 16, 16))
            painter.end()
            return pixmap

        def _on_state_changed(self, state: AssistantState) -> None:
            self._bridge.state_changed.emit(state)

        def _apply_state(self, state: AssistantState) -> None:
            self._state = state
            self._update_bubble()
            self._update_tray_tooltip()
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
            menu = QMenu(self)

            toggle_action = menu.addAction(
                "Hide Avatar" if self.isVisible() else "Show Avatar"
            )
            listen_action = menu.addAction("Start Listening")
            menu.addSeparator()
            quit_action = menu.addAction("Quit Vasya")

            chosen_action = menu.exec(event.globalPos())
            if chosen_action == toggle_action:
                self.toggle_avatar_visibility()
            elif chosen_action == listen_action:
                self._activate_interaction()
            elif chosen_action == quit_action:
                self.quit_application()

        def _activate_interaction(self) -> None:
            if self._interaction_lock.locked():
                log_voice_event("widget_activation_ignored reason=interaction_in_progress")
                return

            def worker() -> None:
                with self._interaction_lock:
                    log_voice_event("widget_activation_started")
                    run_voice_interaction()

            threading.Thread(target=worker, daemon=True).start()

        def closeEvent(self, event) -> None:
            if not self._allow_close:
                event.ignore()
                self.hide_avatar()
                return

            self._save_position()
            self._bubble.close()
            if self._hotkey_listener is not None:
                self._hotkey_listener.stop()
            if self._tray is not None:
                self._tray.hide()
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
            if not text or self._state.name == AssistantStateName.IDLE or not self.isVisible():
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
            target_pos = saved_pos or _default_position()
            self.move(_clamp_to_visible_area(target_pos, self.width(), self.height()))

        def _save_position(self) -> None:
            _save_position(self.pos())

        def _start_hotkey_listener(self) -> None:
            try:
                from pynput import keyboard
            except ImportError:
                log("pynput is not installed. Global hotkey support is disabled.")
                return

            activation_hotkey = normalize_hotkey_combination(HOTKEY_COMBINATION)
            exit_hotkey = normalize_hotkey_combination(HOTKEY_EXIT_COMBINATION)
            hotkeys = {
                activation_hotkey: self._activate_interaction,
                exit_hotkey: self.close,
            }
            try:
                self._hotkey_listener = keyboard.GlobalHotKeys(hotkeys)
            except ValueError as exc:
                log(f"Invalid hotkey configuration. Global hotkeys disabled: {exc}")
                self._hotkey_listener = None
                return
            self._hotkey_listener.start()
            log(
                f"Avatar widget hotkeys enabled. Activation: {activation_hotkey}. "
                f"Exit: {exit_hotkey}."
            )

        def _setup_tray(self) -> None:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                log("System tray is not available on this platform.")
                return

            self._tray = QSystemTrayIcon(QIcon(self._tray_icon_pixmap), self)
            self._tray.setToolTip("Vasya AI")

            menu = QMenu()
            self._toggle_avatar_action = QAction("Hide Avatar", self)
            self._toggle_avatar_action.triggered.connect(self.toggle_avatar_visibility)
            menu.addAction(self._toggle_avatar_action)

            listen_action = QAction("Start Listening", self)
            listen_action.triggered.connect(self._activate_interaction)
            menu.addAction(listen_action)

            menu.addSeparator()

            quit_action = QAction("Quit Vasya", self)
            quit_action.triggered.connect(self.quit_application)
            menu.addAction(quit_action)

            self._tray.setContextMenu(menu)
            self._tray.activated.connect(self._on_tray_activated)
            self._tray.show()
            self._update_tray_tooltip()

        def _on_tray_activated(self, reason) -> None:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                self.toggle_avatar_visibility()

        def toggle_avatar_visibility(self) -> None:
            if self.isVisible():
                self.hide_avatar()
            else:
                self.show_avatar()

        def show_avatar(self) -> None:
            self.show()
            self.raise_()
            self.activateWindow()
            self._update_bubble()
            self._update_toggle_action()

        def hide_avatar(self) -> None:
            self._save_position()
            self._bubble.hide()
            self.hide()
            self._update_toggle_action()

        def quit_application(self) -> None:
            self._allow_close = True
            self.close()
            QApplication.instance().quit()

        def _update_toggle_action(self) -> None:
            if self._tray is None:
                return
            self._toggle_avatar_action.setText("Hide Avatar" if self.isVisible() else "Show Avatar")

        def _update_tray_tooltip(self) -> None:
            if self._tray is None:
                return
            suffix = ""
            if self._state.name != AssistantStateName.IDLE:
                suffix = f" [{self._state.name.value}]"
            self._tray.setToolTip(f"Vasya AI{suffix}")

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

    def _default_position() -> QPoint:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return QPoint(100, 100)

        available = screen.availableGeometry()
        default_x = max(24, available.right() - AVATAR_SIZE - 48)
        default_y = max(24, available.bottom() - AVATAR_SIZE - 120)
        return QPoint(default_x, default_y)

    def _clamp_to_visible_area(position: QPoint, width: int, height: int) -> QPoint:
        for screen in QGuiApplication.screens():
            available = screen.availableGeometry()
            max_x = available.right() - width
            max_y = available.bottom() - height
            if (
                available.left() <= position.x() <= max_x
                and available.top() <= position.y() <= max_y
            ):
                return position

        primary = QGuiApplication.primaryScreen()
        if primary is None:
            return QPoint(100, 100)

        available = primary.availableGeometry()
        clamped_x = min(max(position.x(), available.left() + 24), available.right() - width)
        clamped_y = min(max(position.y(), available.top() + 24), available.bottom() - height)
        return QPoint(clamped_x, clamped_y)

    def _save_position(position: QPoint) -> None:
        state_path = Path(AVATAR_STATE_FILE)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"x": int(position.x()), "y": int(position.y())}
        try:
            state_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError as exc:
            log(f"Failed to save avatar position: {exc}")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    widget = AvatarWidget()
    widget.show()
    log("Avatar widget started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
