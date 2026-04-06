from __future__ import annotations

import json
import math
import sys
import threading
import time
from pathlib import Path

from assistant.child_mode import child_mode_store
from assistant.control import AssistantControlAction
from assistant.state import AssistantState, AssistantStateName, assistant_state
from config.settings import (
    AVATAR_CUSTOM_SKIN_FILE,
    AVATAR_IMAGE_PATH,
    AVATAR_SKIN,
    AVATAR_SIZE,
    AVATAR_STATE_FILE,
    HOTKEY_COMBINATION,
    HOTKEY_EXIT_COMBINATION,
    INTERRUPT_LISTEN_DELAY_SECONDS,
)
from utils.hotkeys import normalize_hotkey_combination
from utils.logger import log, log_voice_event
from utils.platform_runtime import get_platform_name
from voice.profiles import get_active_voice_profile, list_voice_profiles
from voice.session import run_voice_interaction
from voice.tts import set_voice_profile, stop_speaking


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
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QInputDialog,
            QLabel,
            QLineEdit,
            QMenu,
            QPushButton,
            QSlider,
            QSystemTrayIcon,
            QVBoxLayout,
            QWidget,
        )
        from PySide6.QtSvg import QSvgRenderer
    except ImportError:
        print("PySide6 is not installed. Run: pip install -r requirements.txt")
        raise SystemExit(1)

    AVATAR_SKINS = {
        "classic": {
            "label": "Классический",
            "motion_speed": 1.0,
            "motion_bob": 1.0,
            "glow_alpha": 1.0,
            "body_top": "#4f86ff",
            "body_mid": "#224eb6",
            "body_bottom": "#08153b",
            "rim": "#6fe3ff",
            "face_center": "#ffffff",
            "face_edge": "#cad8f2",
            "eye_top": "#2c56be",
            "eye_mid": "#122869",
            "eye_bottom": "#071131",
            "mouth": "#1e2c63",
            "tuft": "#2e5fe0",
            "cheek": "#7ad6ff",
            "glow_idle": "#4f8fff",
            "glow_listening": "#3ec8ff",
            "glow_thinking": "#6fa8ff",
            "glow_speaking": "#5b7cff",
            "glow_error": "#ff6b6b",
        },
        "soft": {
            "label": "Мягкий",
            "motion_speed": 0.92,
            "motion_bob": 0.88,
            "glow_alpha": 0.92,
            "body_top": "#71b4ff",
            "body_mid": "#3f78d8",
            "body_bottom": "#13285f",
            "rim": "#a8ecff",
            "face_center": "#fffdfd",
            "face_edge": "#dbe6fb",
            "eye_top": "#4f7be3",
            "eye_mid": "#274391",
            "eye_bottom": "#10214f",
            "mouth": "#29407d",
            "tuft": "#5b8ef2",
            "cheek": "#a4e4ff",
            "glow_idle": "#74b8ff",
            "glow_listening": "#69dcff",
            "glow_thinking": "#8dbbff",
            "glow_speaking": "#7d96ff",
            "glow_error": "#ff8f95",
        },
        "sunset": {
            "label": "Теплый",
            "motion_speed": 0.96,
            "motion_bob": 0.95,
            "glow_alpha": 1.08,
            "body_top": "#ff9f6e",
            "body_mid": "#d95f64",
            "body_bottom": "#4b2048",
            "rim": "#ffd0a3",
            "face_center": "#fff8f3",
            "face_edge": "#f2d9d3",
            "eye_top": "#8447d0",
            "eye_mid": "#4b2f7f",
            "eye_bottom": "#24163d",
            "mouth": "#5b2a52",
            "tuft": "#ff9e88",
            "cheek": "#ffc1c2",
            "glow_idle": "#ff9c75",
            "glow_listening": "#ffb87f",
            "glow_thinking": "#caa1ff",
            "glow_speaking": "#ff7a90",
            "glow_error": "#ff5f76",
        },
        "mint": {
            "label": "Свежий",
            "motion_speed": 1.08,
            "motion_bob": 1.04,
            "glow_alpha": 1.02,
            "body_top": "#73f0d0",
            "body_mid": "#28a9a5",
            "body_bottom": "#103a52",
            "rim": "#c1fff0",
            "face_center": "#fbfffd",
            "face_edge": "#d9f3ea",
            "eye_top": "#2f7ca5",
            "eye_mid": "#16456f",
            "eye_bottom": "#0b2339",
            "mouth": "#1f5571",
            "tuft": "#48d2ba",
            "cheek": "#aff7ef",
            "glow_idle": "#64e9cf",
            "glow_listening": "#7af8e2",
            "glow_thinking": "#93dfff",
            "glow_speaking": "#5fc8ff",
            "glow_error": "#ff7d88",
        },
        "child": {
            "label": "Детский",
            "motion_speed": 1.18,
            "motion_bob": 1.22,
            "glow_alpha": 1.12,
            "body_top": "#8ec5ff",
            "body_mid": "#6d7cff",
            "body_bottom": "#362f7c",
            "rim": "#ffe28f",
            "face_center": "#fffdf8",
            "face_edge": "#f6e8ff",
            "eye_top": "#6a4fe3",
            "eye_mid": "#3b2c98",
            "eye_bottom": "#1f1951",
            "mouth": "#5a3fa5",
            "tuft": "#ffb86b",
            "cheek": "#ffc2d8",
            "glow_idle": "#8dbdff",
            "glow_listening": "#7de6ff",
            "glow_thinking": "#b1a7ff",
            "glow_speaking": "#ffb3d5",
            "glow_error": "#ff7f9c",
        },
        "minimal": {
            "label": "Минималистичный",
            "motion_speed": 0.82,
            "motion_bob": 0.7,
            "glow_alpha": 0.8,
            "body_top": "#dce7ff",
            "body_mid": "#95acd8",
            "body_bottom": "#3e5177",
            "rim": "#f7fbff",
            "face_center": "#ffffff",
            "face_edge": "#edf3ff",
            "eye_top": "#566783",
            "eye_mid": "#334056",
            "eye_bottom": "#182131",
            "mouth": "#4a5873",
            "tuft": "#8b9cbc",
            "cheek": "#dbe6ff",
            "glow_idle": "#b7c8ea",
            "glow_listening": "#d5e6ff",
            "glow_thinking": "#c7d2e8",
            "glow_speaking": "#a8c0e8",
            "glow_error": "#f0a5ae",
        },
    }

    def _avatar_skin_spec(skin_id: str | None) -> dict:
        default_skin = _avatar_skins()[AVATAR_SKIN] if AVATAR_SKIN in _avatar_skins() else _avatar_skins()["classic"]
        return _avatar_skins().get(skin_id or "", default_skin)

    def _avatar_skin_ids() -> list[str]:
        return list(_avatar_skins().keys())

    def _avatar_skins() -> dict[str, dict]:
        skins = dict(AVATAR_SKINS)
        custom_skin = _load_custom_skin_spec()
        if custom_skin is not None:
            skins["custom"] = custom_skin
        return skins

    def _custom_skin_path() -> Path:
        return Path(AVATAR_CUSTOM_SKIN_FILE)

    def _normalize_custom_skin_spec(payload: dict) -> dict:
        base = dict(AVATAR_SKINS["classic"])
        label = str(payload.get("label", "Пользовательский")).strip() or "Пользовательский"
        base["label"] = label

        for key in (
            "body_top",
            "body_mid",
            "body_bottom",
            "rim",
            "face_center",
            "face_edge",
            "eye_top",
            "eye_mid",
            "eye_bottom",
            "mouth",
            "tuft",
            "cheek",
            "glow_idle",
            "glow_listening",
            "glow_thinking",
            "glow_speaking",
            "glow_error",
        ):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                base[key] = value.strip()

        for key in ("motion_speed", "motion_bob", "glow_alpha"):
            value = payload.get(key)
            if isinstance(value, (int, float)):
                base[key] = float(value)

        return base

    def _load_custom_skin_spec() -> dict | None:
        path = _custom_skin_path()
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        return _normalize_custom_skin_spec(payload)

    def _save_custom_skin_spec(payload: dict) -> None:
        path = _custom_skin_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = _normalize_custom_skin_spec(payload)
        path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _delete_custom_skin_spec() -> None:
        path = _custom_skin_path()
        if path.exists():
            path.unlink()

    def _exportable_skin_spec(skin_id: str | None) -> dict:
        skin = dict(_avatar_skin_spec(skin_id))
        skin.setdefault("label", "Пользовательский")
        return skin

    if get_platform_name() == "macos":
        from scripts.autostart_macos import install_autostart, is_autostart_enabled, uninstall_autostart
    else:
        def is_autostart_enabled() -> bool:
            return False

        def install_autostart() -> None:
            raise RuntimeError("Autostart is currently available only on macOS.")

        def uninstall_autostart() -> None:
            return None

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

    class SettingsDialog(QDialog):
        def __init__(self, widget: "AvatarWidget") -> None:
            super().__init__(widget)
            self.setWindowTitle("Настройки Васи")
            self.setModal(True)
            self.setMinimumWidth(400)
            self._widget = widget
            self.setStyleSheet(
                """
                QDialog {
                    background-color: #0b1435;
                    border: 1px solid #274a99;
                    border-radius: 18px;
                }
                QLabel {
                    color: #e9f2ff;
                    font-size: 13px;
                }
                QCheckBox {
                    color: #eef5ff;
                    spacing: 8px;
                    font-size: 13px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1px solid #4d74d6;
                    background: #13204e;
                }
                QCheckBox::indicator:checked {
                    background: #4f8fff;
                    border: 1px solid #7ab6ff;
                }
                QComboBox, QLineEdit {
                    background: #13204e;
                    color: #f4f8ff;
                    border: 1px solid #345ab3;
                    border-radius: 10px;
                    padding: 8px 10px;
                    min-height: 18px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 22px;
                }
                QComboBox QAbstractItemView {
                    background: #13204e;
                    color: #f4f8ff;
                    border: 1px solid #345ab3;
                    border-radius: 10px;
                    selection-background-color: #2e5ec9;
                    selection-color: #ffffff;
                    outline: 0;
                }
                QSlider::groove:horizontal {
                    border: 0;
                    height: 6px;
                    background: #18306d;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #7ddcff;
                    border: 1px solid #b0ecff;
                    width: 16px;
                    margin: -6px 0;
                    border-radius: 8px;
                }
                QDialogButtonBox QPushButton {
                    background: #173377;
                    color: #f5f9ff;
                    border: 1px solid #3c67d1;
                    border-radius: 10px;
                    padding: 8px 14px;
                    min-width: 100px;
                }
                QDialogButtonBox QPushButton:hover {
                    background: #1d439c;
                }
                """
            )

            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 18)
            layout.setSpacing(14)

            title = QLabel("Настройки Васи", self)
            title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
            subtitle = QLabel(
                "Управление поведением виджета, автозапуском и голосовой активацией.",
                self,
            )
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet("font-size: 12px; color: #9fb8ec;")
            layout.addWidget(title)
            layout.addWidget(subtitle)

            preview_wrap = QWidget(self)
            preview_wrap.setStyleSheet(
                """
                QWidget {
                    background: qradialgradient(cx:0.5, cy:0.4, radius:0.8,
                        fx:0.5, fy:0.4,
                        stop:0 #17357a,
                        stop:1 #0b1435);
                    border: 1px solid #274a99;
                    border-radius: 16px;
                }
                """
            )
            preview_layout = QVBoxLayout(preview_wrap)
            preview_layout.setContentsMargins(12, 10, 12, 12)
            preview_layout.setSpacing(8)
            preview_title = QLabel("Превью", self)
            preview_title.setStyleSheet("font-size: 12px; color: #b9cdf3; font-weight: 600;")
            preview_layout.addWidget(preview_title)
            self._preview = _AvatarPreview(widget, self)
            preview_layout.addWidget(self._preview, alignment=Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(preview_wrap)

            form = QFormLayout()
            form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
            form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(12)

            self._size_combo = QComboBox(self)
            for label, size in (("Маленький", 180), ("Средний", 210), ("Большой", 270)):
                self._size_combo.addItem(label, size)
            self._select_combo_value(self._size_combo, widget._avatar_size)
            self._size_combo.currentIndexChanged.connect(self._sync_preview)
            form.addRow("Размер Васи", self._size_combo)

            self._skin_combo = QComboBox(self)
            self._skin_combo.currentIndexChanged.connect(self._sync_preview)
            self._reload_skin_choices(widget._avatar_skin)

            skin_actions = QHBoxLayout()
            import_skin_button = QPushButton("Импорт палитры...", self)
            import_skin_button.clicked.connect(self._import_custom_skin)
            skin_actions.addWidget(import_skin_button)
            export_skin_button = QPushButton("Экспорт палитры...", self)
            export_skin_button.clicked.connect(self._export_current_skin)
            skin_actions.addWidget(export_skin_button)
            reset_skin_button = QPushButton("Сбросить свою", self)
            reset_skin_button.clicked.connect(self._reset_custom_skin)
            skin_actions.addWidget(reset_skin_button)
            skin_actions.addStretch(1)

            skin_row = QVBoxLayout()
            skin_row.setSpacing(8)
            skin_row.addWidget(self._skin_combo)
            skin_row.addLayout(skin_actions)
            form.addRow("Скин Васи", skin_row)

            image_actions = QHBoxLayout()
            choose_image_button = QPushButton("Выбрать изображение...", self)
            choose_image_button.clicked.connect(self._choose_avatar_image)
            image_actions.addWidget(choose_image_button)
            reset_image_button = QPushButton("Вернуть встроенный", self)
            reset_image_button.clicked.connect(self._reset_avatar_image)
            image_actions.addWidget(reset_image_button)
            image_actions.addStretch(1)
            form.addRow("Картинка Васи", image_actions)

            self._voice_profile_combo = QComboBox(self)
            active_profile = get_active_voice_profile()
            for profile in list_voice_profiles():
                self._voice_profile_combo.addItem(
                    f"{profile.label} ({profile.gender})",
                    profile.profile_id,
                )
            self._select_combo_value(self._voice_profile_combo, active_profile.profile_id)
            form.addRow("Голос Васи", self._voice_profile_combo)

            self._tray_click_combo = QComboBox(self)
            self._tray_click_combo.addItem("Показать или скрыть Васю", "toggle")
            self._tray_click_combo.addItem("Начать слушать", "listen")
            self._select_combo_value(self._tray_click_combo, widget._tray_click_action)
            form.addRow("Клик по иконке в трее", self._tray_click_combo)

            self._opacity_slider = QSlider(Qt.Orientation.Horizontal, self)
            self._opacity_slider.setMinimum(70)
            self._opacity_slider.setMaximum(100)
            self._opacity_slider.setSingleStep(5)
            self._opacity_slider.setValue(int(widget._avatar_opacity * 100))
            opacity_row = QHBoxLayout()
            opacity_row.addWidget(self._opacity_slider)
            self._opacity_label = QLabel(f"{int(widget._avatar_opacity * 100)}%")
            opacity_row.addWidget(self._opacity_label)
            self._opacity_slider.valueChanged.connect(
                lambda value: self._opacity_label.setText(f"{value}%")
            )
            self._opacity_slider.valueChanged.connect(self._sync_preview)
            form.addRow("Прозрачность Васи", opacity_row)

            self._show_bubble_checkbox = QCheckBox("Показывать пузырь ответа", self)
            self._show_bubble_checkbox.setChecked(widget._show_response_bubble)
            form.addRow(self._show_bubble_checkbox)

            self._child_mode_checkbox = QCheckBox("Детский режим", self)
            self._child_mode_checkbox.setChecked(child_mode_store.is_enabled())
            form.addRow(self._child_mode_checkbox)

            self._idle_motion_checkbox = QCheckBox("Плавное движение в покое", self)
            self._idle_motion_checkbox.setChecked(widget._idle_motion_enabled)
            self._idle_motion_checkbox.toggled.connect(self._sync_preview)
            form.addRow(self._idle_motion_checkbox)

            self._snap_checkbox = QCheckBox("Прилипать к краю экрана", self)
            self._snap_checkbox.setChecked(widget._snap_to_edge_enabled)
            form.addRow(self._snap_checkbox)

            self._start_hidden_checkbox = QCheckBox("Запускать скрытым", self)
            self._start_hidden_checkbox.setChecked(widget._start_hidden)
            form.addRow(self._start_hidden_checkbox)

            if get_platform_name() == "macos":
                self._autostart_checkbox = QCheckBox("Запускать при входе", self)
                self._autostart_checkbox.setChecked(widget._launch_at_login_enabled)
                form.addRow(self._autostart_checkbox)
            else:
                self._autostart_checkbox = None

            self._hotkey_input = QLineEdit(widget._activation_hotkey, self)
            form.addRow("Горячая клавиша", self._hotkey_input)

            layout.addLayout(form)

            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                self,
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

            self._sync_preview()

        def apply(self) -> None:
            self._widget._set_avatar_size(int(self._size_combo.currentData()))
            selected_skin = str(self._skin_combo.currentData())
            desired_child_mode = self._child_mode_checkbox.isChecked()
            self._widget._avatar_skin = selected_skin
            self._widget._auto_child_skin = not (
                desired_child_mode and selected_skin != "child"
            )
            selected_profile_id = str(self._voice_profile_combo.currentData())
            if selected_profile_id != get_active_voice_profile().profile_id:
                set_voice_profile(selected_profile_id)
            self._widget._tray_click_action = str(self._tray_click_combo.currentData())
            self._widget._avatar_opacity = self._opacity_slider.value() / 100.0
            self._widget._show_response_bubble = self._show_bubble_checkbox.isChecked()
            if desired_child_mode:
                child_mode_store.enable()
            else:
                child_mode_store.disable()
            self._widget._idle_motion_enabled = self._idle_motion_checkbox.isChecked()
            self._widget._snap_to_edge_enabled = self._snap_checkbox.isChecked()
            self._widget._start_hidden = self._start_hidden_checkbox.isChecked()

            if self._autostart_checkbox is not None:
                desired_autostart = self._autostart_checkbox.isChecked()
                if desired_autostart != self._widget._launch_at_login_enabled:
                    if desired_autostart:
                        install_autostart()
                    else:
                        uninstall_autostart()
                    self._widget._launch_at_login_enabled = desired_autostart

            hotkey_value = self._hotkey_input.text().strip()
            if hotkey_value and hotkey_value != self._widget._activation_hotkey:
                self._widget._apply_hotkey(hotkey_value)

            if not self._widget._show_response_bubble:
                self._widget._bubble.hide()
            else:
                self._widget._update_bubble()

            if self._widget._snap_to_edge_enabled:
                self._widget.move(
                    _snap_to_nearest_edge(
                        self._widget.pos(),
                        self._widget.width(),
                        self._widget.height(),
                    )
                )
                self._widget._update_bubble_position()

            self._widget._last_effective_skin = self._widget._effective_avatar_skin()
            self._widget._tray_icon_pixmap = self._widget._build_tray_pixmap()
            if self._widget._tray is not None:
                self._widget._tray.setIcon(QIcon(self._widget._tray_icon_pixmap))
            self._widget.update()
            self._widget._save_position()

        @staticmethod
        def _select_combo_value(combo: "QComboBox", expected_value) -> None:
            for index in range(combo.count()):
                if combo.itemData(index) == expected_value:
                    combo.setCurrentIndex(index)
                    return

        def _reload_skin_choices(self, selected_skin: str | None = None) -> None:
            current_signal_state = self._skin_combo.blockSignals(True)
            self._skin_combo.clear()
            for skin_id in _avatar_skin_ids():
                self._skin_combo.addItem(_avatar_skin_spec(skin_id)["label"], skin_id)
            self._skin_combo.blockSignals(current_signal_state)
            resolved_skin = selected_skin if selected_skin in _avatar_skin_ids() else AVATAR_SKIN
            self._select_combo_value(self._skin_combo, resolved_skin)

        def _import_custom_skin(self) -> None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выбери JSON-палитру",
                str(Path.cwd()),
                "JSON Files (*.json)",
            )
            if not file_path:
                return
            try:
                payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("JSON должен содержать объект с цветами палитры.")
                _save_custom_skin_spec(payload)
            except Exception as exc:
                log(f"Не удалось импортировать палитру: {exc}")
                return
            self._reload_skin_choices("custom")
            self._sync_preview()

        def _reset_custom_skin(self) -> None:
            _delete_custom_skin_spec()
            current_skin = str(self._skin_combo.currentData())
            self._reload_skin_choices(
                AVATAR_SKIN if current_skin == "custom" else current_skin
            )
            self._sync_preview()

        def _export_current_skin(self) -> None:
            current_skin = str(self._skin_combo.currentData())
            suggested_name = f"vasya_{current_skin or 'skin'}.json"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить палитру Васи",
                str(Path.cwd() / suggested_name),
                "JSON Files (*.json)",
            )
            if not file_path:
                return
            try:
                Path(file_path).write_text(
                    json.dumps(
                        _exportable_skin_spec(current_skin),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            except OSError as exc:
                log(f"Не удалось сохранить палитру: {exc}")

        def _choose_avatar_image(self) -> None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выбери изображение Васи",
                str(Path.cwd()),
                "Images (*.png *.svg *.jpg *.jpeg *.webp)",
            )
            if not file_path:
                return
            chosen = Path(file_path).expanduser()
            if not chosen.exists():
                log(f"Не удалось выбрать изображение: файл не найден {chosen}")
                return
            self._widget._set_avatar_image_path(chosen)
            self._sync_preview()

        def _reset_avatar_image(self) -> None:
            self._widget._set_avatar_image_path(None)
            self._sync_preview()

        def _sync_preview(self) -> None:
            selected_skin = str(self._skin_combo.currentData())
            child_mode_enabled = self._child_mode_checkbox.isChecked()
            auto_child_skin = not (child_mode_enabled and selected_skin != "child")
            self._preview.update_preview(
                size=int(self._size_combo.currentData()),
                skin_id=selected_skin,
                child_mode_enabled=child_mode_enabled,
                auto_child_skin=auto_child_skin,
                opacity=self._opacity_slider.value() / 100.0,
                idle_motion=self._idle_motion_checkbox.isChecked(),
            )

    class _AvatarPreview(QWidget):
        def __init__(self, widget: "AvatarWidget", parent: QWidget | None = None) -> None:
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

        def paintEvent(self, event) -> None:
            _ = event
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setOpacity(max(0.45, min(1.0, self._preview_opacity)))
            preview_bounds = QRectF(10, 10, self.width() - 20, self.height() - 20)
            effective_skin = (
                "child"
                if self._preview_child_mode_enabled and self._preview_auto_child_skin
                else self._preview_skin_id
            )
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
                    scale=max(0.82, min(1.18, self._preview_size / 210.0)),
                    skin_id=effective_skin,
                    smile_bounce=0.0,
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
            self._avatar_skin = str(self._widget_state.get("avatar_skin", AVATAR_SKIN))
            if self._avatar_skin not in _avatar_skin_ids():
                self._avatar_skin = AVATAR_SKIN if AVATAR_SKIN in _avatar_skin_ids() else "classic"
            self._auto_child_skin = bool(self._widget_state.get("auto_child_skin", True))
            self._tray_click_action = str(
                self._widget_state.get("tray_click_action", "toggle")
            )
            self._show_response_bubble = bool(
                self._widget_state.get("show_response_bubble", True)
            )
            self._idle_motion_enabled = bool(
                self._widget_state.get("idle_motion_enabled", True)
            )
            self._snap_to_edge_enabled = bool(
                self._widget_state.get("snap_to_edge_enabled", True)
            )
            self._avatar_opacity = float(self._widget_state.get("avatar_opacity", 1.0))
            self._start_hidden = bool(self._widget_state.get("start_hidden", False))
            self._first_run_done = bool(self._widget_state.get("first_run_done", False))
            self._first_run_pending = bool(self._widget_state.get("first_run_pending", False))
            self._launch_at_login_enabled = is_autostart_enabled()
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
            self._smile_bounce = 0.0
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
            self._last_effective_skin = self._effective_avatar_skin()

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
            self._maybe_run_onboarding()

        def _resolve_avatar_path(self) -> Path | None:
            override_path = str(self._widget_state.get("avatar_image_path", "")).strip()
            if override_path:
                path = Path(override_path).expanduser()
                if path.exists():
                    return path
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

            skin = _avatar_skin_spec(self._effective_avatar_skin())
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(skin["body_mid"]))
            painter.setPen(QPen(QColor(skin["rim"]), 2))
            painter.drawEllipse(QRectF(3, 3, 26, 26))
            painter.setBrush(QColor(skin["face_center"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(8, 8, 16, 16))
            painter.end()
            return pixmap

        def _on_state_changed(self, state: AssistantState) -> None:
            self._bridge.state_changed.emit(state)

        def _apply_state(self, state: AssistantState) -> None:
            previous_state = self._state.name
            self._state = state
            if previous_state == AssistantStateName.SPEAKING and state.name == AssistantStateName.IDLE:
                self._smile_bounce = 1.0
            self._update_bubble()
            self._update_tray_tooltip()
            self.update()

        def _tick(self) -> None:
            if self._state.name == AssistantStateName.IDLE and not self._idle_motion_enabled:
                self._pulse = 0.0
                self._bob = 0.0
            else:
                speed = _animation_speed(self._state.name, self._effective_avatar_skin())
                self._pulse = (self._pulse + speed) % 6.28
                self._bob = (self._bob + speed * 0.7) % 6.28
            self._smile_bounce = max(0.0, self._smile_bounce - 0.07)
            effective_skin = self._effective_avatar_skin()
            if effective_skin != self._last_effective_skin:
                self._last_effective_skin = effective_skin
                self._tray_icon_pixmap = self._build_tray_pixmap()
                if self._tray is not None:
                    self._tray.setIcon(QIcon(self._tray_icon_pixmap))
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
                    if self._snap_to_edge_enabled:
                        self.move(_snap_to_nearest_edge(self.pos(), self.width(), self.height()))
                        self._update_bubble_position()
                    self._save_position()

        def contextMenuEvent(self, event) -> None:
            menu = QMenu(self)

            toggle_action = menu.addAction(
                "Скрыть Васю" if self.isVisible() else "Показать Васю"
            )
            listen_action = menu.addAction("Начать слушать")
            settings_action = menu.addAction("Настройки...")
            menu.addSeparator()
            quit_action = menu.addAction("Закрыть Васю")

            chosen_action = menu.exec(event.globalPos())
            if chosen_action == toggle_action:
                self.toggle_avatar_visibility()
            elif chosen_action == listen_action:
                self._activate_interaction()
            elif chosen_action == settings_action:
                self._open_settings_dialog()
            elif chosen_action == quit_action:
                self.quit_application()

        def _activate_interaction(self) -> None:
            if self._interaction_lock.locked():
                if assistant_state.get().name == AssistantStateName.SPEAKING:
                    log_voice_event("widget_activation_interrupt_speaking")
                    stop_speaking()
                    self._queue_followup_interaction()
                    return
                else:
                    log_voice_event("widget_activation_ignored reason=interaction_in_progress")
                    return

            self._start_interaction_thread("widget_activation_started")

        def _queue_followup_interaction(self) -> None:
            def delayed_worker() -> None:
                with self._interaction_lock:
                    pass
                time.sleep(INTERRUPT_LISTEN_DELAY_SECONDS)
                self._start_interaction_thread("widget_activation_followup_started")

            threading.Thread(target=delayed_worker, daemon=True).start()

        def _start_interaction_thread(self, log_event: str) -> None:
            def worker() -> None:
                with self._interaction_lock:
                    log_voice_event(log_event)
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
            painter.setOpacity(max(0.45, min(1.0, self._avatar_opacity)))

            if self._avatar:
                self._paint_ambient_glow(painter)
                self._paint_avatar(painter)
            else:
                self._paint_character(painter)

        def _paint_ambient_glow(self, painter: QPainter) -> None:
            glow = _animated_glow(
                self._state.name,
                self._pulse,
                self._effective_avatar_skin(),
            )
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

        def _paint_preview_image_avatar(
            self,
            painter: QPainter,
            bounds: QRectF,
            *,
            pulse: float,
            bob: float,
            skin_id: str,
        ) -> None:
            painter.save()
            scale_x = bounds.width() / self.width()
            scale_y = bounds.height() / self.height()
            painter.translate(bounds.left(), bounds.top())
            painter.scale(scale_x, scale_y)

            glow = _animated_glow(self._state.name, pulse, skin_id)
            painter.setPen(Qt.PenStyle.NoPen)

            outer_glow = QRadialGradient(
                self.width() * 0.5,
                self.height() * 0.48,
                self.width() * 0.48,
            )
            outer_glow.setColorAt(0.0, glow)
            fade = QColor(glow)
            fade.setAlpha(max(0, glow.alpha() - 90))
            outer_glow.setColorAt(0.55, fade)
            transparent = QColor(glow)
            transparent.setAlpha(0)
            outer_glow.setColorAt(1.0, transparent)
            painter.setBrush(outer_glow)
            painter.drawEllipse(QRectF(0, 0, self.width(), self.height()))

            bob_offset = _avatar_bob_offset(self._state.name, bob, skin_id)
            shadow_alpha = 65 + int(20 * abs(math.sin(bob)))
            painter.setBrush(QColor(11, 23, 66, shadow_alpha))
            shadow_width = self.width() - 36 + _shadow_width_delta(self._state.name, pulse, skin_id)
            shadow_x = (self.width() - shadow_width) / 2
            painter.drawEllipse(QRectF(shadow_x, self.height() - 26, shadow_width, 14))

            avatar_pixmap = self._prepare_avatar_pixmap(self.width() + 12, self.height() + 16)
            if not avatar_pixmap.isNull():
                draw_x = int((self.width() - avatar_pixmap.width()) / 2)
                draw_y = int((self.height() - avatar_pixmap.height()) / 2) - 2 + int(bob_offset)
                painter.drawPixmap(draw_x, draw_y, avatar_pixmap)

            highlight_path = QPainterPath()
            highlight_path.addEllipse(QRectF(18, 20 + bob_offset, self.width() - 36, self.height() - 44))
            painter.setPen(QPen(_highlight_color(self._state.name, pulse, skin_id), 2))
            painter.drawPath(highlight_path)
            painter.restore()

        def _paint_avatar(self, painter: QPainter) -> None:
            bob_offset = _avatar_bob_offset(
                self._state.name,
                self._bob,
                self._effective_avatar_skin(),
            )
            avatar_rect = QRectF(-6, -12 + bob_offset, self.width() + 12, self.height() + 16)
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            shadow_alpha = 65 + int(20 * abs(math.sin(self._bob)))
            painter.setBrush(QColor(11, 23, 66, shadow_alpha))
            shadow_width = self.width() - 36 + _shadow_width_delta(
                self._state.name,
                self._pulse,
                self._effective_avatar_skin(),
            )
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
            painter.setPen(
                QPen(
                    _highlight_color(
                        self._state.name,
                        self._pulse,
                        self._effective_avatar_skin(),
                    ),
                    2,
                )
            )
            painter.drawPath(highlight_path)
            painter.restore()

        def _set_avatar_image_path(self, path: Path | None) -> None:
            if path is None:
                self._widget_state.pop("avatar_image_path", None)
                self._avatar_path = self._resolve_avatar_path()
            else:
                resolved = Path(path).expanduser()
                self._widget_state["avatar_image_path"] = str(resolved)
                self._avatar_path = resolved

            self._avatar = self._load_avatar()
            self._avatar_is_svg = (
                self._avatar_path is not None and self._avatar_path.suffix.lower() == ".svg"
            )
            self._tray_icon_pixmap = self._build_tray_pixmap()
            if self._tray is not None:
                self._tray.setIcon(QIcon(self._tray_icon_pixmap))
            self.update()
            self._save_position()

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
            self._paint_preview_character(
                painter,
                QRectF(0, 0, self.width(), self.height()),
                pulse=self._pulse,
                bob=self._bob,
                scale=1.0,
                skin_id=self._effective_avatar_skin(),
                smile_bounce=self._smile_bounce,
            )

        def _paint_preview_character(
            self,
            painter: QPainter,
            bounds: QRectF,
            *,
            pulse: float,
            bob: float,
            scale: float,
            skin_id: str | None = None,
            smile_bounce: float = 0.0,
        ) -> None:
            painter.save()
            painter.translate(bounds.left(), bounds.top())
            painter.scale(bounds.width() / self.width(), bounds.height() / self.height())

            original_pulse = self._pulse
            original_bob = self._bob
            self._pulse = pulse
            self._bob = bob

            skin = _avatar_skin_spec(skin_id or self._avatar_skin)
            bob_offset = _avatar_bob_offset(self._state.name, self._bob, skin_id or self._avatar_skin)
            glow = _animated_glow(self._state.name, self._pulse, skin_id or self._avatar_skin)

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
            shadow_width = self.width() * (0.54 * scale) + _shadow_width_delta(
                self._state.name,
                self._pulse,
                skin_id or self._avatar_skin,
            )
            shadow_x = (self.width() - shadow_width) / 2
            painter.setBrush(QColor(9, 18, 54, shadow_alpha))
            painter.drawEllipse(QRectF(shadow_x, self.height() - 30, shadow_width, 16))

            body_rect = QRectF(self.width() * 0.10, self.height() * 0.18 + bob_offset, self.width() * 0.80, self.height() * 0.74)
            body_gradient = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.right(), body_rect.bottom())
            body_gradient.setColorAt(0.0, QColor(skin["body_top"]))
            body_gradient.setColorAt(0.32, QColor(skin["body_mid"]))
            body_gradient.setColorAt(0.75, QColor(skin["body_mid"]).darker(145))
            body_gradient.setColorAt(1.0, QColor(skin["body_bottom"]))

            painter.setBrush(body_gradient)
            painter.setPen(QPen(QColor(skin["rim"]), 3))
            painter.drawEllipse(body_rect)

            rim_path = QPainterPath()
            rim_path.addEllipse(body_rect.adjusted(4, 4, -4, -4))
            rim_color = QColor(skin["rim"])
            rim_color.setAlpha(95 + int(30 * abs(math.sin(self._pulse))))
            painter.setPen(QPen(rim_color, 2))
            painter.drawPath(rim_path)

            listening_lift = _listening_face_lift(self._state.name, self._pulse)
            face_rect = QRectF(
                self.width() * 0.20,
                self.height() * 0.23 + bob_offset + listening_lift,
                self.width() * 0.60,
                self.height() * 0.48,
            )
            face_gradient = QRadialGradient(face_rect.center().x(), face_rect.center().y(), face_rect.width() * 0.72)
            face_gradient.setColorAt(0.0, QColor(skin["face_center"]))
            face_gradient.setColorAt(0.72, QColor(skin["face_center"]).darker(104))
            face_gradient.setColorAt(1.0, QColor(skin["face_edge"]))
            painter.setBrush(face_gradient)
            painter.setPen(QPen(QColor("#d9e6ff"), 1))
            painter.drawEllipse(face_rect)

            painter.setBrush(QColor(255, 255, 255, 125))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(self.width() * 0.63, self.height() * 0.24 + bob_offset, self.width() * 0.13, self.height() * 0.08))

            eye_w = self.width() * 0.17
            eye_h = self.height() * 0.21
            eye_y = self.height() * 0.38 + bob_offset + listening_lift * 0.55
            left_eye = QRectF(self.width() * 0.28, eye_y, eye_w, eye_h)
            right_eye = QRectF(self.width() * 0.55, eye_y, eye_w, eye_h)
            blink = _blink_scale(self._state.name, self._pulse)
            visible_eye_height = max(eye_h * (0.18 + blink * 0.82), eye_h * 0.18)
            eye_vertical_shift = (eye_h - visible_eye_height) * 0.48
            gaze_x, gaze_y = _eye_gaze_offset(self._state.name, self._pulse)
            speaking_squint = _speaking_eye_squint(self._state.name, self._pulse)
            visible_eye_height *= speaking_squint

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
                eye_gradient.setColorAt(0.0, QColor(skin["eye_top"]))
                eye_gradient.setColorAt(0.35, QColor(skin["eye_mid"]))
                eye_gradient.setColorAt(1.0, QColor(skin["eye_bottom"]))
                painter.setBrush(eye_gradient)
                painter.setPen(QPen(QColor(skin["eye_top"]).lighter(122), 1))
                painter.drawRoundedRect(
                    adjusted_rect,
                    adjusted_rect.width() * 0.48,
                    adjusted_rect.height() * 0.48,
                )

                inner_shadow = QRadialGradient(
                    adjusted_rect.center().x() + adjusted_rect.width() * 0.08,
                    adjusted_rect.center().y() + adjusted_rect.height() * 0.1,
                    adjusted_rect.width() * 0.62,
                )
                inner_shadow.setColorAt(0.0, QColor(255, 255, 255, 22))
                inner_shadow.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setBrush(inner_shadow)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(
                    adjusted_rect.adjusted(
                        adjusted_rect.width() * 0.08,
                        adjusted_rect.height() * 0.1,
                        -adjusted_rect.width() * 0.08,
                        -adjusted_rect.height() * 0.12,
                    ),
                    adjusted_rect.width() * 0.36,
                    adjusted_rect.height() * 0.36,
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
                else:
                    pupil_size = min(adjusted_rect.width(), adjusted_rect.height()) * 0.22
                    pupil_rect = QRectF(
                        adjusted_rect.center().x() - pupil_size * 0.5 + adjusted_rect.width() * gaze_x,
                        adjusted_rect.center().y() - pupil_size * 0.46 + adjusted_rect.height() * gaze_y,
                        pupil_size,
                        pupil_size,
                    )
                    painter.setBrush(QColor(255, 255, 255, 72))
                    painter.drawEllipse(
                        QRectF(
                            pupil_rect.left() + pupil_size * 0.18,
                            pupil_rect.top() + pupil_size * 0.1,
                            pupil_size * 0.42,
                            pupil_size * 0.42,
                        )
                    )

            draw_eye(left_eye)
            draw_eye(right_eye)

            mouth_pen = QPen(QColor(skin["mouth"]), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(mouth_pen)
            mouth_rect = QRectF(
                self.width() * 0.41,
                self.height() * 0.58 + bob_offset,
                self.width() * 0.18,
                self.height() * 0.10,
            )
            mouth_start, mouth_span, mouth_y_shift, mouth_width_scale = _mouth_expression(
                self._state.name,
                self._pulse,
                smile_bounce,
            )
            mouth_rect.moveTop(mouth_rect.top() + mouth_y_shift)
            mouth_rect.setWidth(mouth_rect.width() * mouth_width_scale)
            mouth_rect.moveLeft(self.width() * 0.5 - mouth_rect.width() * 0.5)
            painter.drawArc(mouth_rect, mouth_start * 16, mouth_span * 16)

            cheek_glow = QRadialGradient(
                self.width() * 0.72,
                self.height() * 0.58 + bob_offset,
                self.width() * 0.10,
            )
            cheek_core = QColor(skin["cheek"])
            cheek_core.setAlpha(min(120, 58 + int(30 * smile_bounce)))
            cheek_edge = QColor(skin["cheek"])
            cheek_edge.setAlpha(0)
            cheek_glow.setColorAt(0.0, cheek_core)
            cheek_glow.setColorAt(1.0, cheek_edge)
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

            tuft_pen = QPen(QColor(skin["tuft"]), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
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

            self._pulse = original_pulse
            self._bob = original_bob
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
            if (
                not self._show_response_bubble
                or not text
                or self._state.name == AssistantStateName.IDLE
                or not self.isVisible()
            ):
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
            primary = QGuiApplication.primaryScreen()
            if primary is not None:
                available = primary.availableGeometry()
                if bubble_x + self._bubble.width() > available.right() - 8:
                    bubble_x = self.x() - self._bubble.width() - 12
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
                    "show_response_bubble": self._show_response_bubble,
                    "idle_motion_enabled": self._idle_motion_enabled,
                    "snap_to_edge_enabled": self._snap_to_edge_enabled,
                    "avatar_opacity": self._avatar_opacity,
                    "avatar_skin": self._avatar_skin,
                    "auto_child_skin": self._auto_child_skin,
                    "start_hidden": not self.isVisible(),
                }
            )

        def _effective_avatar_skin(self) -> str:
            if child_mode_store.is_enabled() and self._auto_child_skin:
                return "child"
            return self._avatar_skin

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
            self._tray.setToolTip("Вася AI")

            menu = QMenu()
            self._toggle_avatar_action = QAction("Скрыть Васю", self)
            self._toggle_avatar_action.triggered.connect(self.toggle_avatar_visibility)
            menu.addAction(self._toggle_avatar_action)

            listen_action = QAction("Начать слушать", self)
            listen_action.triggered.connect(self._activate_interaction)
            menu.addAction(listen_action)

            settings_action = QAction("Настройки...", self)
            settings_action.triggered.connect(self._open_settings_dialog)
            menu.addAction(settings_action)
            menu.addSeparator()

            quit_action = QAction("Закрыть Васю", self)
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
            if self._first_run_pending and not self._first_run_done:
                self._first_run_pending = False
                self._widget_state["first_run_pending"] = False
                self._run_onboarding_flow(autostart_settings=True)

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
            self._toggle_avatar_action.setText("Скрыть Васю" if self.isVisible() else "Показать Васю")

        def _update_tray_tooltip(self) -> None:
            if self._tray is None:
                return
            suffix = ""
            if self._state.name != AssistantStateName.IDLE:
                suffix = f" [{_state_label(self._state.name)}]"
            self._tray.setToolTip(f"Вася AI{suffix}")

        def _open_settings_dialog(self) -> None:
            dialog = SettingsDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    dialog.apply()
                except Exception as exc:
                    log(f"Failed to apply settings: {exc}")

        def _maybe_run_onboarding(self) -> None:
            if self._first_run_done:
                return
            if self._start_hidden:
                self._first_run_pending = True
                self._widget_state["first_run_pending"] = True
                self._save_position()
                return
            self._run_onboarding_flow(autostart_settings=True)

        def _run_onboarding_flow(self, *, autostart_settings: bool) -> None:
            if self._first_run_done:
                return
            self._first_run_done = True
            self._widget_state["first_run_done"] = True
            self._widget_state["first_run_pending"] = False
            self._save_position()

            def show_onboarding():
                if not self.isVisible():
                    self.show_avatar()
                hotkey_hint = self._activation_hotkey or HOTKEY_COMBINATION
                message = (
                    "Привет. Я Вася и я рядом.\n"
                    f"Горячая клавиша: {hotkey_hint}\n"
                    "Клик по мне — начать говорить, правый клик — меню.\n"
                    "Скажи «пока», чтобы закрыть, или «замолчи», чтобы остановить речь.\n"
                    "Настройки — в меню, если нужно."
                )
                assistant_state.set(AssistantStateName.IDLE, message)
                self._update_bubble()
                def clear_onboarding():
                    current = assistant_state.get()
                    if current.name == AssistantStateName.IDLE and current.message == message:
                        assistant_state.set(AssistantStateName.IDLE)
                        self._update_bubble()
                QTimer.singleShot(8000, clear_onboarding)
                if autostart_settings:
                    QTimer.singleShot(800, self._open_settings_dialog)

            QTimer.singleShot(300, show_onboarding)

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
                "Горячая клавиша",
                "Введи сочетание в формате pynput:",
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

        def _apply_hotkey(self, hotkey_text: str) -> None:
            new_hotkey = normalize_hotkey_combination(hotkey_text)
            old_hotkey = self._activation_hotkey
            self._activation_hotkey = new_hotkey

            if self._hotkey_listener is not None:
                self._hotkey_listener.stop()
                self._hotkey_listener = None

            self._start_hotkey_listener()
            if self._hotkey_listener is None:
                self._activation_hotkey = old_hotkey
                self._start_hotkey_listener()
                raise RuntimeError("Не удалось применить горячую клавишу.")

            self._save_position()

    def _glow_color(state_name: AssistantStateName, skin_id: str | None = None) -> str:
        skin = _avatar_skin_spec(skin_id)
        if state_name == AssistantStateName.LISTENING:
            return skin["glow_listening"]
        if state_name == AssistantStateName.THINKING:
            return skin["glow_thinking"]
        if state_name == AssistantStateName.SPEAKING:
            return skin["glow_speaking"]
        if state_name == AssistantStateName.ERROR:
            return skin["glow_error"]
        return skin["glow_idle"]

    def _animation_speed(state_name: AssistantStateName, skin_id: str | None = None) -> float:
        skin = _avatar_skin_spec(skin_id)
        if state_name == AssistantStateName.LISTENING:
            speed = 0.12
        elif state_name == AssistantStateName.THINKING:
            speed = 0.08
        elif state_name == AssistantStateName.SPEAKING:
            speed = 0.20
        elif state_name == AssistantStateName.ERROR:
            speed = 0.22
        else:
            speed = 0.05
        return speed * float(skin.get("motion_speed", 1.0))

    def _animated_glow(state_name: AssistantStateName, pulse: float, skin_id: str | None = None) -> QColor:
        skin = _avatar_skin_spec(skin_id)
        base = QColor(_glow_color(state_name, skin_id))
        if state_name == AssistantStateName.LISTENING:
            alpha = 125 + int(42 * (0.55 + 0.45 * math.sin(pulse * 1.15)))
        elif state_name == AssistantStateName.THINKING:
            alpha = 104 + int(24 * (0.5 + 0.5 * math.sin(pulse * 0.72)))
        elif state_name == AssistantStateName.SPEAKING:
            alpha = 128 + int(72 * abs(math.sin(pulse * 1.85)))
        elif state_name == AssistantStateName.ERROR:
            alpha = 120 + int(80 * abs(math.sin(pulse * 2.0)))
        else:
            alpha = 90 + int(12 * (0.5 + 0.5 * math.sin(pulse * 0.55)))
        base.setAlpha(int(alpha * float(skin.get("glow_alpha", 1.0))))
        return base

    def _avatar_bob_offset(
        state_name: AssistantStateName,
        bob: float,
        skin_id: str | None = None,
    ) -> float:
        skin = _avatar_skin_spec(skin_id)
        if state_name == AssistantStateName.LISTENING:
            value = -1.8 * abs(math.sin(bob * 0.9))
        elif state_name == AssistantStateName.THINKING:
            value = -1.0 * math.sin(bob * 0.8)
        elif state_name == AssistantStateName.SPEAKING:
            value = -3.8 * abs(math.sin(bob * 1.35))
        elif state_name == AssistantStateName.ERROR:
            value = 1.2 * math.sin(bob * 2.4)
        else:
            value = -0.45 * math.sin(bob * 0.7)
        return value * float(skin.get("motion_bob", 1.0))

    def _shadow_width_delta(
        state_name: AssistantStateName,
        pulse: float,
        skin_id: str | None = None,
    ) -> float:
        skin = _avatar_skin_spec(skin_id)
        if state_name == AssistantStateName.SPEAKING:
            value = -7 * abs(math.sin(pulse * 1.6))
        elif state_name == AssistantStateName.LISTENING:
            value = -3 * abs(math.sin(pulse * 0.9))
        else:
            value = -2 * abs(math.sin(pulse))
        return value * float(skin.get("motion_bob", 1.0))

    def _highlight_color(state_name: AssistantStateName, pulse: float, skin_id: str | None = None) -> QColor:
        color = QColor(_glow_color(state_name, skin_id))
        color.setAlpha(105 + int(35 * abs(math.sin(pulse))))
        return color

    def _eye_gaze_offset(state_name: AssistantStateName, pulse: float) -> tuple[float, float]:
        if state_name == AssistantStateName.LISTENING:
            return (0.04 * math.sin(pulse * 0.8), -0.03)
        if state_name == AssistantStateName.THINKING:
            return (0.07 * math.sin(pulse * 0.45), -0.05)
        if state_name == AssistantStateName.SPEAKING:
            return (0.03 * math.sin(pulse * 1.4), 0.01)
        if state_name == AssistantStateName.ERROR:
            return (0.08 * math.sin(pulse * 2.0), -0.02)
        return (0.025 * math.sin(pulse * 0.5), 0.0)

    def _speaking_eye_squint(state_name: AssistantStateName, pulse: float) -> float:
        if state_name == AssistantStateName.SPEAKING:
            return 0.9 + 0.1 * abs(math.sin(pulse * 1.6))
        if state_name == AssistantStateName.LISTENING:
            return 1.02
        return 1.0

    def _listening_face_lift(state_name: AssistantStateName, pulse: float) -> float:
        if state_name == AssistantStateName.LISTENING:
            return -1.4 - 0.6 * abs(math.sin(pulse * 0.95))
        return 0.0

    def _mouth_expression(
        state_name: AssistantStateName,
        pulse: float,
        smile_bounce: float = 0.0,
    ) -> tuple[float, float, float, float]:
        if state_name == AssistantStateName.LISTENING:
            return (202, 134, -1.1, 1.04)
        if state_name == AssistantStateName.THINKING:
            return (215, 112, 0.5 * math.sin(pulse * 0.7), 0.96)
        if state_name == AssistantStateName.SPEAKING:
            return (
                198,
                145 + 18 * abs(math.sin(pulse * 1.9)),
                -1.2 * abs(math.sin(pulse * 1.5)),
                1.05,
            )
        if state_name == AssistantStateName.ERROR:
            return (225, 86, 1.6 * abs(math.sin(pulse * 1.8)), 0.9)
        return (
            205 - int(6 * smile_bounce),
            130 + int(26 * smile_bounce),
            -1.8 * smile_bounce,
            1.0 + 0.08 * smile_bounce,
        )

    def _state_label(state_name: AssistantStateName) -> str:
        if state_name == AssistantStateName.LISTENING:
            return "слушает"
        if state_name == AssistantStateName.THINKING:
            return "думает"
        if state_name == AssistantStateName.SPEAKING:
            return "говорит"
        if state_name == AssistantStateName.ERROR:
            return "ошибка"
        return "в покое"

    def _blink_scale(state_name: AssistantStateName, pulse: float) -> float:
        if state_name == AssistantStateName.THINKING:
            return 0.90 + 0.10 * abs(math.sin(pulse * 0.55))
        if state_name == AssistantStateName.ERROR:
            return 0.88 + 0.12 * abs(math.sin(pulse * 1.6))

        blink_wave = max(0.0, math.sin(pulse * 0.62))
        if blink_wave > 0.985:
            return 0.22
        if blink_wave > 0.95:
            return 0.55
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

    def _widget_visible_on_start() -> bool:
        payload = _load_widget_state()
        return not bool(payload.get("start_hidden", False))

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

    def _snap_to_nearest_edge(position: QPoint, width: int, height: int) -> QPoint:
        primary = QGuiApplication.primaryScreen()
        if primary is None:
            return position

        available = primary.availableGeometry()
        clamped = _clamp_to_visible_area(position, width, height)
        left_x = available.left() + 16
        right_x = available.right() - width - 16
        target_x = left_x if abs(clamped.x() - left_x) <= abs(clamped.x() - right_x) else right_x
        return QPoint(target_x, clamped.y())

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
    if _widget_visible_on_start():
        widget.show()
    else:
        widget.hide()
    log("Avatar widget started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
