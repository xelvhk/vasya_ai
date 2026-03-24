from __future__ import annotations

import json
import math
import sys
import threading
from pathlib import Path

from assistant.control import AssistantControlAction
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
from voice.tts import stop_speaking


def main() -> None:
    try:
        from PySide6.QtCore import QObject, QPoint, QRectF, Qt, QTimer, Signal
        from PySide6.QtGui import (
            QAction,
            QActionGroup,
            QColor,
            QFont,
            QGuiApplication,
            QImage,
            QIcon,
            QLinearGradient,
            QMouseEvent,
            QPainter,
            QPainterPath,
            QPen,
            QPixmap,
            QRadialGradient,
        )
        from PySide6.QtWidgets import QApplication, QInputDialog, QMenu, QSystemTrayIcon, QWidget
        from PySide6.QtSvg import QSvgRenderer
    except ImportError:
        print("PySide6 is not installed. Run: pip install -r requirements.txt")
        raise SystemExit(1)

    class StateBridge(QObject):
        state_changed = Signal(object)
        exit_requested = Signal()

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
            self._widget_state = _load_widget_state()
            self._avatar_size = int(self._widget_state.get("size", AVATAR_SIZE))
            self._tray_click_action = str(
                self._widget_state.get("tray_click_action", "toggle")
            )
            self._activation_hotkey = str(
                self._widget_state.get("hotkey_combination", HOTKEY_COMBINATION)
            )
            self.setFixedSize(self._avatar_size, self._avatar_size)

            self._drag_pos: QPoint | None = None
            self._press_pos: QPoint | None = None
            self._interaction_lock = threading.Lock()
            self._state = assistant_state.get()
            self._pulse = 0.0
            self._bob = 0.0
            self._avatar_path = self._resolve_avatar_path()
            self._avatar = self._load_avatar()
            self._avatar_is_svg = (
                self._avatar_path is not None and self._avatar_path.suffix.lower() == ".svg"
            )
            self._tray_icon_pixmap = self._build_tray_pixmap()
            self._bridge = StateBridge()
            self._bubble = ResponseBubble()
            self._hotkey_listener = None
            self._tray = None
            self._allow_close = False

            self._bridge.state_changed.connect(self._apply_state)
            self._bridge.exit_requested.connect(self.quit_application)
            assistant_state.subscribe(self._on_state_changed)

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(60)

            self._restore_position()
            self._update_bubble()
            self._start_hotkey_listener()
            self._setup_tray()

        def _resolve_avatar_path(self) -> Path | None:
            if not AVATAR_IMAGE_PATH:
                return None
            path = Path(AVATAR_IMAGE_PATH).expanduser()
            if not path.exists():
                return None
            return path

        def _load_avatar(self):
            path = self._avatar_path
            if path is None:
                return None
            if path.suffix.lower() == ".svg":
                return self._render_svg_avatar(512)
            pixmap = QPixmap(str(path))
            return pixmap if not pixmap.isNull() else None

        def _build_tray_pixmap(self) -> QPixmap:
            if self._avatar:
                return self._prepare_avatar_pixmap(32, 32)

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
            speed = _animation_speed(self._state.name)
            self._pulse = (self._pulse + speed) % 6.28
            self._bob = (self._bob + speed * 0.7) % 6.28
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
            settings_menu = self._build_settings_menu(menu)
            menu.addSeparator()
            quit_action = menu.addAction("Quit Vasya")

            chosen_action = menu.exec(event.globalPos())
            if chosen_action == toggle_action:
                self.toggle_avatar_visibility()
            elif chosen_action == listen_action:
                self._activate_interaction()
            elif chosen_action == quit_action:
                self.quit_application()
            elif chosen_action is not None:
                self._handle_settings_action(chosen_action)

        def _activate_interaction(self) -> None:
            if self._interaction_lock.locked():
                if assistant_state.get().name == AssistantStateName.SPEAKING:
                    log_voice_event("widget_activation_interrupt_speaking")
                    stop_speaking()
                else:
                    log_voice_event("widget_activation_ignored reason=interaction_in_progress")
                    return

            def worker() -> None:
                with self._interaction_lock:
                    log_voice_event("widget_activation_started")
                    action = run_voice_interaction()
                    if action == AssistantControlAction.EXIT:
                        self._bridge.exit_requested.emit()

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

            if self._avatar:
                self._paint_ambient_glow(painter)
                self._paint_avatar(painter)
            else:
                self._paint_character(painter)

        def _paint_ambient_glow(self, painter: QPainter) -> None:
            glow = _animated_glow(self._state.name, self._pulse)
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)

            outer_glow = QRadialGradient(self.width() * 0.5, self.height() * 0.48, self.width() * 0.48)
            outer_glow.setColorAt(0.0, glow)
            fade = QColor(glow)
            fade.setAlpha(max(0, glow.alpha() - 90))
            outer_glow.setColorAt(0.55, fade)
            transparent = QColor(glow)
            transparent.setAlpha(0)
            outer_glow.setColorAt(1.0, transparent)
            painter.setBrush(outer_glow)
            painter.drawEllipse(QRectF(0, 0, self.width(), self.height()))
            painter.restore()

        def _paint_avatar(self, painter: QPainter) -> None:
            bob_offset = _avatar_bob_offset(self._state.name, self._bob)
            avatar_rect = QRectF(-6, -12 + bob_offset, self.width() + 12, self.height() + 16)
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            shadow_alpha = 65 + int(20 * abs(math.sin(self._bob)))
            painter.setBrush(QColor(11, 23, 66, shadow_alpha))
            shadow_width = self.width() - 36 + _shadow_width_delta(self._state.name, self._pulse)
            shadow_x = (self.width() - shadow_width) / 2
            painter.drawEllipse(QRectF(shadow_x, self.height() - 26, shadow_width, 14))

            avatar_pixmap = self._prepare_avatar_pixmap(
                int(avatar_rect.width()),
                int(avatar_rect.height()),
            )
            if not avatar_pixmap.isNull():
                draw_x = int((self.width() - avatar_pixmap.width()) / 2)
                draw_y = int((self.height() - avatar_pixmap.height()) / 2) - 2 + int(bob_offset)
                painter.drawPixmap(draw_x, draw_y, avatar_pixmap)

            highlight_path = QPainterPath()
            highlight_path.addEllipse(QRectF(18, 20 + bob_offset, self.width() - 36, self.height() - 44))
            painter.setPen(QPen(_highlight_color(self._state.name, self._pulse), 2))
            painter.drawPath(highlight_path)
            painter.restore()

        def _prepare_avatar_pixmap(self, width: int, height: int) -> QPixmap:
            if self._avatar_path is None:
                return QPixmap()

            if self._avatar_is_svg:
                return self._render_svg_avatar(max(width, height))

            if not self._avatar:
                return QPixmap()

            source = self._avatar
            return source.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        def _render_svg_avatar(self, size: int) -> QPixmap:
            if self._avatar_path is None:
                return QPixmap()

            renderer = QSvgRenderer(str(self._avatar_path))
            if not renderer.isValid():
                return QPixmap()

            canvas_size = max(64, size)
            image = QImage(canvas_size, canvas_size, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)

            svg_painter = QPainter(image)
            svg_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            svg_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            render_rect = QRectF(
                canvas_size * -0.05,
                canvas_size * -0.10,
                canvas_size * 1.10,
                canvas_size * 1.12,
            )
            renderer.render(svg_painter, render_rect)
            svg_painter.end()
            return QPixmap.fromImage(image)

        def _paint_fallback(self, painter: QPainter) -> None:
            self._paint_character(painter)

        def _paint_character(self, painter: QPainter) -> None:
            bob_offset = _avatar_bob_offset(self._state.name, self._bob)
            glow = _animated_glow(self._state.name, self._pulse)

            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)

            ambient = QRadialGradient(self.width() * 0.5, self.height() * 0.46, self.width() * 0.52)
            ambient.setColorAt(0.0, glow)
            ambient_fade = QColor(glow)
            ambient_fade.setAlpha(max(0, glow.alpha() - 110))
            ambient.setColorAt(0.62, ambient_fade)
            ambient_clear = QColor(glow)
            ambient_clear.setAlpha(0)
            ambient.setColorAt(1.0, ambient_clear)
            painter.setBrush(ambient)
            painter.drawEllipse(QRectF(-8, -6, self.width() + 16, self.height() + 12))

            shadow_alpha = 70 + int(18 * abs(math.sin(self._bob)))
            shadow_width = self.width() * 0.54 + _shadow_width_delta(self._state.name, self._pulse)
            shadow_x = (self.width() - shadow_width) / 2
            painter.setBrush(QColor(9, 18, 54, shadow_alpha))
            painter.drawEllipse(QRectF(shadow_x, self.height() - 30, shadow_width, 16))

            body_rect = QRectF(self.width() * 0.10, self.height() * 0.18 + bob_offset, self.width() * 0.80, self.height() * 0.74)
            body_gradient = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.right(), body_rect.bottom())
            body_gradient.setColorAt(0.0, QColor("#4f86ff"))
            body_gradient.setColorAt(0.32, QColor("#224eb6"))
            body_gradient.setColorAt(0.75, QColor("#0f245f"))
            body_gradient.setColorAt(1.0, QColor("#08153b"))

            painter.setBrush(body_gradient)
            painter.setPen(QPen(QColor("#6fe3ff"), 3))
            painter.drawEllipse(body_rect)

            rim_path = QPainterPath()
            rim_path.addEllipse(body_rect.adjusted(4, 4, -4, -4))
            painter.setPen(QPen(QColor(120, 222, 255, 95 + int(30 * abs(math.sin(self._pulse)))), 2))
            painter.drawPath(rim_path)

            face_rect = QRectF(self.width() * 0.20, self.height() * 0.23 + bob_offset, self.width() * 0.60, self.height() * 0.48)
            face_gradient = QRadialGradient(face_rect.center().x(), face_rect.center().y(), face_rect.width() * 0.72)
            face_gradient.setColorAt(0.0, QColor("#ffffff"))
            face_gradient.setColorAt(0.72, QColor("#eef3ff"))
            face_gradient.setColorAt(1.0, QColor("#cad8f2"))
            painter.setBrush(face_gradient)
            painter.setPen(QPen(QColor("#d9e6ff"), 1))
            painter.drawEllipse(face_rect)

            painter.setBrush(QColor(255, 255, 255, 125))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(self.width() * 0.63, self.height() * 0.24 + bob_offset, self.width() * 0.13, self.height() * 0.08))

            eye_w = self.width() * 0.17
            eye_h = self.height() * 0.21
            eye_y = self.height() * 0.38 + bob_offset
            left_eye = QRectF(self.width() * 0.28, eye_y, eye_w, eye_h)
            right_eye = QRectF(self.width() * 0.55, eye_y, eye_w, eye_h)
            blink = _blink_scale(self._state.name, self._pulse)
            visible_eye_height = max(eye_h * (0.18 + blink * 0.82), eye_h * 0.18)
            eye_vertical_shift = (eye_h - visible_eye_height) * 0.48

            def draw_eye(rect: QRectF) -> None:
                adjusted_rect = QRectF(
                    rect.left(),
                    rect.top() + eye_vertical_shift,
                    rect.width(),
                    visible_eye_height,
                )
                eye_gradient = QRadialGradient(
                    adjusted_rect.center().x(),
                    adjusted_rect.top() + adjusted_rect.height() * 0.34,
                    adjusted_rect.width() * 0.88,
                )
                eye_gradient.setColorAt(0.0, QColor("#2c56be"))
                eye_gradient.setColorAt(0.35, QColor("#122869"))
                eye_gradient.setColorAt(1.0, QColor("#071131"))
                painter.setBrush(eye_gradient)
                painter.setPen(QPen(QColor("#456ee0"), 1))
                painter.drawRoundedRect(
                    adjusted_rect,
                    adjusted_rect.width() * 0.48,
                    adjusted_rect.height() * 0.48,
                )

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#eef3ff"))
                top_lid = QPainterPath()
                top_lid.moveTo(rect.left() - 2, rect.top() + rect.height() * 0.08)
                top_lid.cubicTo(
                    rect.left() + rect.width() * 0.18,
                    rect.top() - rect.height() * 0.08,
                    rect.left() + rect.width() * 0.82,
                    rect.top() - rect.height() * 0.08,
                    rect.right() + 2,
                    rect.top() + rect.height() * 0.08,
                )
                top_lid.lineTo(rect.right() + 2, adjusted_rect.top())
                top_lid.lineTo(rect.left() - 2, adjusted_rect.top())
                top_lid.closeSubpath()
                painter.drawPath(top_lid)

                bottom_lid = QPainterPath()
                bottom_lid.moveTo(rect.left() - 2, adjusted_rect.bottom())
                bottom_lid.lineTo(rect.right() + 2, adjusted_rect.bottom())
                bottom_lid.cubicTo(
                    rect.left() + rect.width() * 0.82,
                    rect.bottom() + rect.height() * 0.08,
                    rect.left() + rect.width() * 0.18,
                    rect.bottom() + rect.height() * 0.08,
                    rect.left() - 2,
                    adjusted_rect.bottom(),
                )
                bottom_lid.closeSubpath()
                painter.drawPath(bottom_lid)

                if blink > 0.45:
                    highlight_size = min(adjusted_rect.width(), adjusted_rect.height()) * 0.24
                    painter.setBrush(QColor("#ffffff"))
                    painter.drawEllipse(
                        QRectF(
                            adjusted_rect.left() + adjusted_rect.width() * 0.38,
                            adjusted_rect.top() + adjusted_rect.height() * 0.16,
                            highlight_size,
                            highlight_size,
                        )
                    )

            draw_eye(left_eye)
            draw_eye(right_eye)

            mouth_pen = QPen(QColor("#1e2c63"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(mouth_pen)
            mouth_rect = QRectF(self.width() * 0.41, self.height() * 0.58 + bob_offset, self.width() * 0.18, self.height() * 0.10)
            painter.drawArc(mouth_rect, 205 * 16, 130 * 16)

            cheek_glow = QRadialGradient(
                self.width() * 0.72,
                self.height() * 0.58 + bob_offset,
                self.width() * 0.10,
            )
            cheek_glow.setColorAt(0.0, QColor(122, 214, 255, 58))
            cheek_glow.setColorAt(1.0, QColor(122, 214, 255, 0))
            painter.setBrush(cheek_glow)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QRectF(
                    self.width() * 0.64,
                    self.height() * 0.49 + bob_offset,
                    self.width() * 0.18,
                    self.height() * 0.18,
                )
            )

            tuft_pen = QPen(QColor("#2e5fe0"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(tuft_pen)
            tuft_path = QPainterPath()
            tuft_path.moveTo(self.width() * 0.48, self.height() * 0.17 + bob_offset)
            tuft_path.cubicTo(
                self.width() * 0.45,
                self.height() * 0.06 + bob_offset,
                self.width() * 0.57,
                self.height() * 0.02 + bob_offset,
                self.width() * 0.61,
                self.height() * 0.13 + bob_offset,
            )
            tuft_path.moveTo(self.width() * 0.52, self.height() * 0.16 + bob_offset)
            tuft_path.cubicTo(
                self.width() * 0.54,
                self.height() * 0.05 + bob_offset,
                self.width() * 0.66,
                self.height() * 0.04 + bob_offset,
                self.width() * 0.69,
                self.height() * 0.16 + bob_offset,
            )
            painter.drawPath(tuft_path)

            painter.restore()

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
            target_pos = saved_pos or _default_position(self.width(), self.height())
            self.move(_clamp_to_visible_area(target_pos, self.width(), self.height()))

        def _save_position(self) -> None:
            _save_widget_state(
                {
                    **self._widget_state,
                    "x": int(self.pos().x()),
                    "y": int(self.pos().y()),
                    "size": self._avatar_size,
                    "tray_click_action": self._tray_click_action,
                    "hotkey_combination": self._activation_hotkey,
                }
            )

        def _start_hotkey_listener(self) -> None:
            try:
                from pynput import keyboard
            except ImportError:
                log("pynput is not installed. Global hotkey support is disabled.")
                return

            activation_hotkey = normalize_hotkey_combination(self._activation_hotkey)
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
            self._build_settings_menu(menu)
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
                if self._tray_click_action == "listen":
                    self._activate_interaction()
                else:
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

        def _build_settings_menu(self, parent_menu: QMenu) -> QMenu:
            settings_menu = parent_menu.addMenu("Settings")

            size_menu = settings_menu.addMenu("Avatar Size")
            self._size_action_group = QActionGroup(self)
            self._size_action_group.setExclusive(True)
            for label, size in (("Small", 180), ("Medium", 210), ("Large", 270)):
                action = size_menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(self._avatar_size == size)
                action.setData(("size", size))
                action.triggered.connect(
                    lambda checked=False, selected_action=action: self._handle_settings_action(selected_action)
                )
                self._size_action_group.addAction(action)

            tray_click_menu = settings_menu.addMenu("Tray Click Action")
            self._tray_action_group = QActionGroup(self)
            self._tray_action_group.setExclusive(True)
            for label, value in (("Toggle Avatar", "toggle"), ("Start Listening", "listen")):
                action = tray_click_menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(self._tray_click_action == value)
                action.setData(("tray_click_action", value))
                action.triggered.connect(
                    lambda checked=False, selected_action=action: self._handle_settings_action(selected_action)
                )
                self._tray_action_group.addAction(action)

            set_hotkey_action = settings_menu.addAction("Set Listening Hotkey...")
            set_hotkey_action.setData(("set_hotkey", None))
            set_hotkey_action.triggered.connect(
                lambda checked=False, selected_action=set_hotkey_action: self._handle_settings_action(selected_action)
            )

            reset_position_action = settings_menu.addAction("Reset Position")
            reset_position_action.setData(("reset_position", None))
            reset_position_action.triggered.connect(
                lambda checked=False, selected_action=reset_position_action: self._handle_settings_action(selected_action)
            )
            return settings_menu

        def _handle_settings_action(self, action: QAction) -> None:
            data = action.data()
            if not isinstance(data, tuple) or len(data) != 2:
                return

            key, value = data
            if key == "size" and isinstance(value, int):
                self._set_avatar_size(value)
            elif key == "tray_click_action" and isinstance(value, str):
                self._tray_click_action = value
                self._save_position()
            elif key == "set_hotkey":
                self._prompt_hotkey()
            elif key == "reset_position":
                self.move(_default_position(self.width(), self.height()))
                self._update_bubble_position()
                self._save_position()

        def _set_avatar_size(self, size: int) -> None:
            self._avatar_size = size
            self.setFixedSize(size, size)
            self._tray_icon_pixmap = self._build_tray_pixmap()
            if self._tray is not None:
                self._tray.setIcon(QIcon(self._tray_icon_pixmap))
            self.move(_clamp_to_visible_area(self.pos(), self.width(), self.height()))
            self._update_bubble_position()
            self._save_position()
            self.update()

        def _prompt_hotkey(self) -> None:
            text, accepted = QInputDialog.getText(
                self,
                "Set Listening Hotkey",
                "Enter hotkey in pynput format:",
                text=self._activation_hotkey,
            )
            if not accepted or not text.strip():
                return

            new_hotkey = normalize_hotkey_combination(text)
            old_hotkey = self._activation_hotkey
            self._activation_hotkey = new_hotkey

            if self._hotkey_listener is not None:
                self._hotkey_listener.stop()
                self._hotkey_listener = None

            self._start_hotkey_listener()
            if self._hotkey_listener is None:
                self._activation_hotkey = old_hotkey
                self._start_hotkey_listener()
                return

            self._save_position()

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

    def _animation_speed(state_name: AssistantStateName) -> float:
        if state_name == AssistantStateName.LISTENING:
            return 0.14
        if state_name == AssistantStateName.THINKING:
            return 0.09
        if state_name == AssistantStateName.SPEAKING:
            return 0.18
        if state_name == AssistantStateName.ERROR:
            return 0.22
        return 0.06

    def _animated_glow(state_name: AssistantStateName, pulse: float) -> QColor:
        base = QColor(_glow_color(state_name))
        if state_name == AssistantStateName.LISTENING:
            alpha = 120 + int(55 * abs(math.sin(pulse)))
        elif state_name == AssistantStateName.THINKING:
            alpha = 105 + int(32 * (0.5 + 0.5 * math.sin(pulse)))
        elif state_name == AssistantStateName.SPEAKING:
            alpha = 125 + int(65 * abs(math.sin(pulse * 1.5)))
        elif state_name == AssistantStateName.ERROR:
            alpha = 120 + int(80 * abs(math.sin(pulse * 2.0)))
        else:
            alpha = 95 + int(18 * abs(math.sin(pulse)))
        base.setAlpha(alpha)
        return base

    def _avatar_bob_offset(state_name: AssistantStateName, bob: float) -> float:
        if state_name == AssistantStateName.LISTENING:
            return -2.5 * abs(math.sin(bob))
        if state_name == AssistantStateName.THINKING:
            return -1.4 * math.sin(bob)
        if state_name == AssistantStateName.SPEAKING:
            return -3.2 * abs(math.sin(bob * 1.2))
        if state_name == AssistantStateName.ERROR:
            return 1.2 * math.sin(bob * 2.4)
        return -0.6 * math.sin(bob)

    def _shadow_width_delta(state_name: AssistantStateName, pulse: float) -> float:
        if state_name == AssistantStateName.SPEAKING:
            return -6 * abs(math.sin(pulse * 1.4))
        if state_name == AssistantStateName.LISTENING:
            return -4 * abs(math.sin(pulse))
        return -2 * abs(math.sin(pulse))

    def _highlight_color(state_name: AssistantStateName, pulse: float) -> QColor:
        color = QColor(_glow_color(state_name))
        color.setAlpha(105 + int(35 * abs(math.sin(pulse))))
        return color

    def _blink_scale(state_name: AssistantStateName, pulse: float) -> float:
        if state_name == AssistantStateName.THINKING:
            return 0.78 + 0.22 * abs(math.sin(pulse * 0.8))
        if state_name == AssistantStateName.ERROR:
            return 0.88 + 0.12 * abs(math.sin(pulse * 1.6))
        return 1.0

    def _load_widget_state() -> dict:
        state_path = Path(AVATAR_STATE_FILE)
        if not state_path.exists():
            return {}
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _load_saved_position() -> QPoint | None:
        payload = _load_widget_state()

        x = payload.get("x")
        y = payload.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return None
        return QPoint(x, y)

    def _default_position(width: int, height: int) -> QPoint:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return QPoint(100, 100)

        available = screen.availableGeometry()
        default_x = max(24, available.right() - width - 48)
        default_y = max(24, available.bottom() - height - 120)
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

    def _save_widget_state(payload: dict) -> None:
        state_path = Path(AVATAR_STATE_FILE)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            state_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError as exc:
            log(f"Failed to save avatar widget state: {exc}")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    widget = AvatarWidget()
    widget.show()
    log("Avatar widget started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
