from __future__ import annotations

import json
import math
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from assistant.child_mode import child_mode_store
from assistant.control import AssistantControlAction, assistant_control
from assistant.state import AssistantState, AssistantStateName, assistant_state
from config.settings import (
    AGENT_ROUTING_PROFILE,
    AUDIO_FILENAME,
    AVATAR_CUSTOM_SKIN_FILE,
    AVATAR_IMAGE_PATH,
    AVATAR_PACK_SKINS,
    AVATAR_SKIN,
    AVATAR_SIZE,
    AVATAR_STATE_FILE,
    CHAT_PROMPT_PACK_PROFILE,
    HOTKEY_COMBINATION,
    HOTKEY_EXIT_COMBINATION,
    HOTKEY_TEXT_COMBINATION,
    MORNING_SHOW_CITY,
    MORNING_SHOW_ENABLED,
    MORNING_SHOW_HOUR_LIMIT,
    MIN_AUDIO_RMS,
    VOICE_SMART_FOLLOWUP_ENABLED,
    VOICE_SMART_FOLLOWUP_LISTEN_SECONDS,
    VOICE_SMART_FOLLOWUP_RETRIES,
    VOICE_AUTO_INTERRUPT_TTS_ENABLED,
    VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS,
    VOICE_AUTO_INTERRUPT_ADAPTIVE_ENABLED,
    VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD,
    VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD,
    VOICE_AUTO_INTERRUPT_HITS_QUIET,
    VOICE_AUTO_INTERRUPT_HITS_NORMAL,
    VOICE_AUTO_INTERRUPT_HITS_NOISY,
    VOICE_RUNTIME_PREWARM_ON_WIDGET_START,
)
from utils.hotkeys import normalize_hotkey_combination
from utils.logger import log, log_voice_event
from utils.platform_runtime import get_platform_name
from services.user_profile_service import clear_user_profile
from services.integration_settings_service import (
    get_integration_setting,
    save_integration_settings,
)
from services.speed_report_service import (
    build_voice_auto_tune_plan,
    build_voice_health_snapshot,
    build_voice_speed_report,
    build_voice_tuning_hints,
)
from services.github_service import GitHubServiceError, fetch_recent_commits
from services.memory_center_service import build_memory_center_summary, get_memory_center_status
from services.memory_scheduler_service import start_memory_background_scheduler
from services.memory_sync_service import sync_memory_source
from services.notion_service import NotionServiceError, read_page_text
from services.morning_show_service import get_morning_show_message, reset_morning_show_today
from services.runtime_prewarm_service import start_runtime_prewarm_async
from voice.profiles import get_active_voice_profile, list_voice_profiles
from voice.pipeline import run_text_pipeline
from voice.recorder import record_audio
from voice.session import run_voice_interaction
from voice.tts import set_voice_profile, speak, stop_speaking


def _run_mic_health_check(duration_seconds: float = 2.0) -> tuple[bool, str]:
    try:
        recording = record_audio(AUDIO_FILENAME, duration_seconds)
        if recording.rms < MIN_AUDIO_RMS:
            return False, "Слышу очень тихо. Попробуй говорить громче или поднести микрофон ближе."
        return True, "Микрофон работает. Слышу тебя."
    except Exception:
        return False, "Не получилось проверить микрофон."


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
            QDoubleSpinBox,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QInputDialog,
            QLabel,
            QLineEdit,
            QMenu,
            QMessageBox,
            QPushButton,
            QProgressBar,
            QSlider,
            QSpinBox,
            QSystemTrayIcon,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )
        from PySide6.QtSvg import QSvgRenderer
    except ImportError:
        print("PySide6 is not installed. Run: pip install -r requirements.txt")
        raise SystemExit(1)

    try:
        from rlottie_python import LottieAnimation
    except ImportError:
        LottieAnimation = None

    BRAND_BG = "#070b1f"
    BRAND_PANEL = "#0c1333"
    BRAND_PANEL_ALT = "#121c47"
    BRAND_BORDER = "#2b4699"
    BRAND_TEXT = "#e9f2ff"
    BRAND_MUTED = "#9fb8ec"
    BRAND_ACCENT = "#22b8ff"
    BRAND_ACCENT_ALT = "#7b3dff"

    def _dialog_brand_stylesheet(extra: str = "") -> str:
        return f"""
            QDialog {{
                background-color: {BRAND_BG};
                border: 1px solid {BRAND_BORDER};
                border-radius: 18px;
            }}
            QLabel {{
                color: {BRAND_TEXT};
                font-size: 13px;
            }}
            QPushButton {{
                background: {BRAND_PANEL_ALT};
                color: #f7faff;
                border: 1px solid #3f5fc7;
                border-radius: 10px;
                padding: 8px 14px;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background: #1a2a66;
                border: 1px solid {BRAND_ACCENT};
            }}
            {extra}
        """

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

    def _pack_manifest_path(pack_id: str) -> Path:
        return Path(__file__).resolve().parent.parent / "assets" / "skins" / pack_id / "manifest.json"

    def _available_pack_skin_ids() -> list[str]:
        result: list[str] = []
        for raw_id in AVATAR_PACK_SKINS:
            pack_id = str(raw_id or "").strip()
            if not pack_id:
                continue
            if _pack_manifest_path(pack_id).exists():
                result.append(pack_id)
        return result

    def _pack_skin_combo_value(pack_id: str) -> str:
        return f"__pack_skin:{pack_id}"

    def _pack_skin_from_combo_value(value: str) -> str | None:
        prefix = "__pack_skin:"
        normalized = str(value or "").strip()
        if not normalized.startswith(prefix):
            return None
        pack_id = normalized[len(prefix):].strip()
        return pack_id or None

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
        text_command_requested = Signal()

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
            self.resize(250, 84)

        def set_text(self, text: str) -> None:
            self._text = text
            self.update()

        def paintEvent(self, event) -> None:
            _ = event
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            bubble_rect = self.rect().adjusted(2, 2, -2, -2)
            gradient = QLinearGradient(bubble_rect.topLeft(), bubble_rect.bottomRight())
            gradient.setColorAt(0.0, QColor("#0f1a45"))
            gradient.setColorAt(0.6, QColor("#111a41"))
            gradient.setColorAt(1.0, QColor("#1a1642"))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor("#4ea8ff"), 1))
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 18, 18)

            painter.setPen(QPen(QColor("#7d4bff"), 1))
            painter.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 16, 16)

            painter.setPen(QColor("#f4f8ff"))
            painter.setFont(QFont("Helvetica", 10))
            painter.drawText(
                self.rect().adjusted(16, 12, -16, -12),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                self._text,
            )

    class HoverBubble(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._text = ""
            self.resize(220, 50)

        def set_text(self, text: str) -> None:
            self._text = text
            self.update()

        def paintEvent(self, event) -> None:
            _ = event
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            bubble_rect = self.rect().adjusted(2, 2, -2, -2)
            gradient = QLinearGradient(bubble_rect.topLeft(), bubble_rect.bottomRight())
            gradient.setColorAt(0.0, QColor("#101a45"))
            gradient.setColorAt(1.0, QColor("#181b43"))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor("#40b5ff"), 1))
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 14, 14)

            painter.setPen(QColor("#e8f0ff"))
            painter.setFont(QFont("Helvetica", 9))
            painter.drawText(
                self.rect().adjusted(12, 8, -12, -8),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                self._text,
            )

    class QuickCommandsDialog(QDialog):
        def __init__(self, widget: "AvatarWidget") -> None:
            super().__init__(widget)
            self._widget = widget
            self.setWindowTitle("Быстрые команды")
            self.setModal(True)
            self.setMinimumWidth(420)
            self.setStyleSheet(_dialog_brand_stylesheet())

            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 18)
            layout.setSpacing(12)

            title = QLabel("Быстрые команды", self)
            title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {BRAND_ACCENT_ALT};")
            layout.addWidget(title)

            subtitle = QLabel("Примеры фраз, которые Вася понимает сразу.", self)
            subtitle.setStyleSheet(f"color: {BRAND_MUTED}; font-size: 12px;")
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)

            hotkey_hint = widget._activation_hotkey or HOTKEY_COMBINATION
            text_hotkey_hint = widget._text_hotkey or HOTKEY_TEXT_COMBINATION
            commands = (
                f"Горячая клавиша: {hotkey_hint}\n"
                f"Текстовая клавиша: {text_hotkey_hint}\n"
                "Клик — начать говорить\n"
                "«пока» — закрыть помощника\n"
                "«замолчи» — остановить речь\n"
                "«какие у меня задачи» — список задач\n"
                "«какие у меня дела» — события\n"
                "«запомни …» — сохранить заметку\n"
                "«запомни, что мне нравится …» — личная память\n"
                "«что ты обо мне помнишь» — показать личную память\n"
                "«очисти личную память» — сбросить личную память (с подтверждением)\n"
                "«синхронизируй github в notion» — обновить страницу проекта\n"
                "«отчет скорости» — показать задержки голосового контура\n"
                "«диагностика скорости» — дать быстрые рекомендации по ускорению\n"
                "«проверь микрофон» — быстрый тест микрофона\n"
                "«подбери настройки голоса» — авто-тюнинг по последним метрикам\n"
                "«выгрузи заметки в обсидиан»\n"
                "«давай играть в слова» — детские игры"
            )
            body = QLabel(commands, self)
            body.setStyleSheet(f"color: {BRAND_TEXT}; font-size: 12px;")
            body.setWordWrap(True)
            layout.addWidget(body)

            buttons_row = QHBoxLayout()
            diagnose_button = QPushButton("Диагностика скорости", self)
            diagnose_button.clicked.connect(self._open_speed_diagnostics)
            buttons_row.addWidget(diagnose_button)
            buttons_row.addStretch(1)
            close_button = QPushButton("Понятно", self)
            close_button.clicked.connect(self.accept)
            buttons_row.addWidget(close_button)
            layout.addLayout(buttons_row)

        def _open_speed_diagnostics(self) -> None:
            self._widget._show_speed_diagnostics()

    class TextCommandDialog(QDialog):
        def __init__(self, widget: "AvatarWidget") -> None:
            super().__init__(widget)
            self.setWindowTitle("Текстовая команда")
            self.setModal(True)
            self.setMinimumWidth(460)
            self._text = ""
            self.setStyleSheet(
                _dialog_brand_stylesheet(
                    f"""
                    QLineEdit {{
                        background: {BRAND_PANEL};
                        color: {BRAND_TEXT};
                        border: 1px solid #3e63c9;
                        border-radius: 10px;
                        padding: 8px 10px;
                        min-height: 20px;
                    }}
                    """
                )
            )

            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 18)
            layout.setSpacing(12)

            title = QLabel("Текстовая команда", self)
            title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {BRAND_ACCENT};")
            layout.addWidget(title)

            subtitle = QLabel(
                "Удобно для точных команд в Notion/GitHub и длинного текста.",
                self,
            )
            subtitle.setStyleSheet(f"color: {BRAND_MUTED}; font-size: 12px;")
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)

            self._input = QLineEdit(self)
            self._input.setPlaceholderText("Например: синхронизируй github xelvhk/vasya_ai в notion")
            self._input.returnPressed.connect(self._submit)
            layout.addWidget(self._input)

            buttons_row = QHBoxLayout()
            buttons_row.setSpacing(10)
            submit_button = QPushButton("Отправить", self)
            submit_button.clicked.connect(self._submit)
            cancel_button = QPushButton("Отмена", self)
            cancel_button.clicked.connect(self.reject)
            buttons_row.addStretch(1)
            buttons_row.addWidget(cancel_button)
            buttons_row.addWidget(submit_button)
            layout.addLayout(buttons_row)

            self._input.setFocus()

        @property
        def command_text(self) -> str:
            return self._text

        def _submit(self) -> None:
            text = " ".join(self._input.text().strip().split())
            if not text:
                self._input.setFocus()
                return
            self._text = text
            self.accept()

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
                    background-color: #070b1f;
                    border: 1px solid #2e489c;
                    border-radius: 18px;
                }
                QLabel {
                    color: #edf4ff;
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
                    border: 1px solid #4b67cb;
                    background: #121c47;
                }
                QCheckBox::indicator:checked {
                    background: #7b3dff;
                    border: 1px solid #22b8ff;
                }
                QComboBox, QLineEdit {
                    background: #121c47;
                    color: #f4f8ff;
                    border: 1px solid #3d61c9;
                    border-radius: 10px;
                    padding: 8px 10px;
                    min-height: 18px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 22px;
                }
                QComboBox QAbstractItemView {
                    background: #121c47;
                    color: #f4f8ff;
                    border: 1px solid #3d61c9;
                    border-radius: 10px;
                    selection-background-color: #224ebd;
                    selection-color: #ffffff;
                    outline: 0;
                }
                QWidget#settingsTabPage {
                    background: #0f173b;
                }
                QTabWidget#settingsTabs {
                    background: transparent;
                }
                QTabWidget#settingsTabs::pane {
                    border: 1px solid #2e489c;
                    border-radius: 12px;
                    background: #0f173b;
                    margin-top: 6px;
                }
                QTabWidget#settingsTabs::tab-bar {
                    alignment: left;
                }
                QTabWidget#settingsTabs > QWidget#qt_tabwidget_stackedwidget {
                    background: #0f173b;
                    border-radius: 10px;
                }
                QTabWidget#settingsTabs QTabBar {
                    background: #0a112c;
                }
                QTabWidget#settingsTabs QTabBar::tab {
                    background: #142454;
                    color: #bfd3fb;
                    border: 1px solid #355dbf;
                    border-bottom: none;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    padding: 7px 12px;
                    margin-right: 6px;
                }
                QTabWidget#settingsTabs QTabBar::tab:selected {
                    background: #1b2f73;
                    color: #ffffff;
                    border: 1px solid #7b3dff;
                }
                QTabWidget#settingsTabs QTabBar::tab:!selected {
                    margin-top: 2px;
                }
                QSlider::groove:horizontal {
                    border: 0;
                    height: 6px;
                    background: #1a2f67;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #22b8ff;
                    border: 1px solid #8ee2ff;
                    width: 16px;
                    margin: -6px 0;
                    border-radius: 8px;
                }
                QPushButton {
                    background: #1a2a66;
                    color: #f5f9ff;
                    border: 1px solid #3f5fc7;
                    border-radius: 10px;
                    padding: 8px 14px;
                }
                QPushButton:hover {
                    background: #213985;
                    border: 1px solid #22b8ff;
                }
                QDialogButtonBox QPushButton {
                    min-width: 100px;
                }
                """
            )

            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 18)
            layout.setSpacing(14)

            title = QLabel("Настройки Васи", self)
            title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {BRAND_ACCENT_ALT};")
            subtitle = QLabel(
                "Управление поведением виджета, автозапуском и голосовой активацией.",
                self,
            )
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet(f"font-size: 12px; color: {BRAND_MUTED};")
            layout.addWidget(title)
            layout.addWidget(subtitle)

            preview_wrap = QWidget(self)
            preview_wrap.setStyleSheet(
                """
                QWidget {
                    background: qradialgradient(cx:0.5, cy:0.4, radius:0.8,
                        fx:0.5, fy:0.4,
                        stop:0 #17295f,
                        stop:0.55 #111b45,
                        stop:1 #070b1f);
                    border: 1px solid #2e489c;
                    border-radius: 16px;
                }
                """
            )
            preview_layout = QVBoxLayout(preview_wrap)
            preview_layout.setContentsMargins(12, 10, 12, 12)
            preview_layout.setSpacing(8)
            preview_title = QLabel("Превью", self)
            preview_title.setStyleSheet(f"font-size: 12px; color: {BRAND_MUTED}; font-weight: 600;")
            preview_layout.addWidget(preview_title)
            self._preview = _AvatarPreview(widget, self)
            preview_layout.addWidget(self._preview, alignment=Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(preview_wrap)

            tabs = QTabWidget(self)
            tabs.setObjectName("settingsTabs")
            tabs.setDocumentMode(True)
            tabs.tabBar().setDrawBase(False)

            appearance_tab = QWidget(self)
            appearance_tab.setObjectName("settingsTabPage")
            behavior_tab = QWidget(self)
            behavior_tab.setObjectName("settingsTabPage")
            integrations_tab = QWidget(self)
            integrations_tab.setObjectName("settingsTabPage")
            tabs.addTab(appearance_tab, "Внешний вид")
            tabs.addTab(behavior_tab, "Поведение")
            tabs.addTab(integrations_tab, "Интеграции")

            appearance_form = QFormLayout(appearance_tab)
            appearance_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
            appearance_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
            appearance_form.setHorizontalSpacing(16)
            appearance_form.setVerticalSpacing(12)

            behavior_form = QFormLayout(behavior_tab)
            behavior_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
            behavior_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
            behavior_form.setHorizontalSpacing(16)
            behavior_form.setVerticalSpacing(12)

            integrations_form = QFormLayout(integrations_tab)
            integrations_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
            integrations_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
            integrations_form.setHorizontalSpacing(16)
            integrations_form.setVerticalSpacing(12)

            self._size_combo = QComboBox(self)
            for label, size in (("Маленький", 180), ("Средний", 210), ("Большой", 270)):
                self._size_combo.addItem(label, size)
            self._select_combo_value(self._size_combo, widget._avatar_size)
            self._size_combo.currentIndexChanged.connect(self._sync_preview)
            appearance_form.addRow("Размер Васи", self._size_combo)

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
            appearance_form.addRow("Скин Васи", skin_row)

            image_actions = QHBoxLayout()
            choose_image_button = QPushButton("Выбрать изображение...", self)
            choose_image_button.clicked.connect(self._choose_avatar_image)
            image_actions.addWidget(choose_image_button)
            reset_image_button = QPushButton("Вернуть встроенный", self)
            reset_image_button.clicked.connect(self._reset_avatar_image)
            image_actions.addWidget(reset_image_button)
            image_actions.addStretch(1)
            appearance_form.addRow("Картинка Васи", image_actions)

            self._voice_profile_combo = QComboBox(self)
            active_profile = get_active_voice_profile()
            for profile in list_voice_profiles():
                self._voice_profile_combo.addItem(
                    f"{profile.label} ({profile.gender})",
                    profile.profile_id,
                )
            self._select_combo_value(self._voice_profile_combo, active_profile.profile_id)
            behavior_form.addRow("Голос Васи", self._voice_profile_combo)

            self._tray_click_combo = QComboBox(self)
            self._tray_click_combo.addItem("Показать или скрыть Васю", "toggle")
            self._tray_click_combo.addItem("Начать слушать", "listen")
            self._select_combo_value(self._tray_click_combo, widget._tray_click_action)
            behavior_form.addRow("Клик по иконке в трее", self._tray_click_combo)

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
            appearance_form.addRow("Прозрачность Васи", opacity_row)

            self._show_bubble_checkbox = QCheckBox("Показывать пузырь ответа", self)
            self._show_bubble_checkbox.setChecked(widget._show_response_bubble)
            behavior_form.addRow(self._show_bubble_checkbox)

            self._child_mode_checkbox = QCheckBox("Детский режим", self)
            self._child_mode_checkbox.setChecked(child_mode_store.is_enabled())
            behavior_form.addRow(self._child_mode_checkbox)

            self._morning_show_checkbox = QCheckBox("Утреннее шоу (первое обращение за день)", self)
            self._morning_show_checkbox.setChecked(widget._morning_show_enabled)
            behavior_form.addRow(self._morning_show_checkbox)

            self._morning_show_city_input = QLineEdit(widget._morning_show_city, self)
            self._morning_show_city_input.setPlaceholderText("Город для погоды, например Moscow")
            behavior_form.addRow("Город утреннего шоу", self._morning_show_city_input)

            self._morning_show_hour_limit = QSpinBox(self)
            self._morning_show_hour_limit.setRange(0, 23)
            self._morning_show_hour_limit.setValue(widget._morning_show_hour_limit)
            behavior_form.addRow("До какого часа", self._morning_show_hour_limit)

            self._smart_followup_checkbox = QCheckBox("Умный follow-up после ответа", self)
            self._smart_followup_checkbox.setChecked(widget._smart_followup_enabled)
            behavior_form.addRow(self._smart_followup_checkbox)

            self._smart_followup_seconds = QDoubleSpinBox(self)
            self._smart_followup_seconds.setRange(1.0, 8.0)
            self._smart_followup_seconds.setSingleStep(0.5)
            self._smart_followup_seconds.setValue(widget._smart_followup_listen_seconds)
            self._smart_followup_seconds.setSuffix(" с")
            behavior_form.addRow("Окно дослушивания", self._smart_followup_seconds)

            self._smart_followup_retries = QSpinBox(self)
            self._smart_followup_retries.setRange(1, 3)
            self._smart_followup_retries.setValue(widget._smart_followup_retries)
            behavior_form.addRow("Повторы в follow-up", self._smart_followup_retries)

            self._auto_interrupt_checkbox = QCheckBox("Прерывать озвучивание новой голосовой командой", self)
            self._auto_interrupt_checkbox.setChecked(widget._auto_interrupt_tts_enabled)
            behavior_form.addRow(self._auto_interrupt_checkbox)

            self._auto_interrupt_sample_seconds = QDoubleSpinBox(self)
            self._auto_interrupt_sample_seconds.setRange(0.5, 3.0)
            self._auto_interrupt_sample_seconds.setSingleStep(0.1)
            self._auto_interrupt_sample_seconds.setValue(widget._auto_interrupt_sample_seconds)
            self._auto_interrupt_sample_seconds.setSuffix(" с")
            behavior_form.addRow("Окно barge-in", self._auto_interrupt_sample_seconds)

            self._auto_interrupt_adaptive_checkbox = QCheckBox(
                "Адаптивный auto-interrupt (тихо/шумно)",
                self,
            )
            self._auto_interrupt_adaptive_checkbox.setChecked(widget._auto_interrupt_adaptive_enabled)
            self._auto_interrupt_adaptive_checkbox.setToolTip(
                "Рекомендуется: включено. В тихой среде прерывает быстрее, в шумной осторожнее."
            )
            behavior_form.addRow(self._auto_interrupt_adaptive_checkbox)

            self._auto_interrupt_quiet_rms = QDoubleSpinBox(self)
            self._auto_interrupt_quiet_rms.setRange(50.0, 600.0)
            self._auto_interrupt_quiet_rms.setSingleStep(5.0)
            self._auto_interrupt_quiet_rms.setValue(widget._auto_interrupt_quiet_rms_threshold)
            self._auto_interrupt_quiet_rms.setSuffix(" RMS")
            self._auto_interrupt_quiet_rms.setToolTip("Рекомендуется: 140 RMS")
            behavior_form.addRow("Порог тихой среды", self._auto_interrupt_quiet_rms)

            self._auto_interrupt_noisy_rms = QDoubleSpinBox(self)
            self._auto_interrupt_noisy_rms.setRange(80.0, 900.0)
            self._auto_interrupt_noisy_rms.setSingleStep(5.0)
            self._auto_interrupt_noisy_rms.setValue(widget._auto_interrupt_noisy_rms_threshold)
            self._auto_interrupt_noisy_rms.setSuffix(" RMS")
            self._auto_interrupt_noisy_rms.setToolTip("Рекомендуется: 260 RMS")
            behavior_form.addRow("Порог шумной среды", self._auto_interrupt_noisy_rms)

            self._auto_interrupt_hits_quiet = QSpinBox(self)
            self._auto_interrupt_hits_quiet.setRange(1, 6)
            self._auto_interrupt_hits_quiet.setValue(widget._auto_interrupt_hits_quiet)
            self._auto_interrupt_hits_quiet.setToolTip("Рекомендуется: 1 подтверждение")
            behavior_form.addRow("Подтверждений (тихо)", self._auto_interrupt_hits_quiet)

            self._auto_interrupt_hits_normal = QSpinBox(self)
            self._auto_interrupt_hits_normal.setRange(1, 6)
            self._auto_interrupt_hits_normal.setValue(widget._auto_interrupt_hits_normal)
            self._auto_interrupt_hits_normal.setToolTip("Рекомендуется: 2 подтверждения")
            behavior_form.addRow("Подтверждений (обычно)", self._auto_interrupt_hits_normal)

            self._auto_interrupt_hits_noisy = QSpinBox(self)
            self._auto_interrupt_hits_noisy.setRange(1, 6)
            self._auto_interrupt_hits_noisy.setValue(widget._auto_interrupt_hits_noisy)
            self._auto_interrupt_hits_noisy.setToolTip("Рекомендуется: 3 подтверждения")
            behavior_form.addRow("Подтверждений (шумно)", self._auto_interrupt_hits_noisy)
            self._auto_interrupt_adaptive_checkbox.toggled.connect(self._sync_auto_interrupt_controls)
            self._auto_interrupt_quiet_rms.valueChanged.connect(self._sync_auto_interrupt_thresholds)
            self._sync_auto_interrupt_controls()

            self._routing_profile_combo = QComboBox(self)
            self._routing_profile_combo.addItem("RolePack v1 (рекомендуется)", "rolepack_v1")
            self._routing_profile_combo.addItem("Classic", "classic_v1")
            self._select_combo_value(self._routing_profile_combo, widget._agent_routing_profile)
            behavior_form.addRow("A/B: Routing профиль", self._routing_profile_combo)

            self._prompt_pack_profile_combo = QComboBox(self)
            self._prompt_pack_profile_combo.addItem("Dynamic v1 (рекомендуется)", "dynamic_v1")
            self._prompt_pack_profile_combo.addItem("Classic", "classic_v1")
            self._select_combo_value(self._prompt_pack_profile_combo, widget._chat_prompt_pack_profile)
            behavior_form.addRow("A/B: Prompt pack профиль", self._prompt_pack_profile_combo)

            tuning_actions = QHBoxLayout()
            auto_tune_button = QPushButton("Подобрать автоматически", self)
            auto_tune_button.clicked.connect(self._run_voice_auto_tune)
            tuning_actions.addWidget(auto_tune_button)
            tuning_actions.addStretch(1)
            behavior_form.addRow("Auto-tune", tuning_actions)

            morning_actions = QHBoxLayout()
            test_morning_show_button = QPushButton("Тест утреннего шоу", self)
            test_morning_show_button.clicked.connect(self._test_morning_show)
            morning_actions.addWidget(test_morning_show_button)
            reset_morning_show_button = QPushButton("Сбросить на сегодня", self)
            reset_morning_show_button.clicked.connect(self._reset_morning_show_today)
            morning_actions.addWidget(reset_morning_show_button)
            morning_actions.addStretch(1)
            behavior_form.addRow("Проверка", morning_actions)

            self._github_repo_input = QLineEdit(
                get_integration_setting("github_default_repo"),
                self,
            )
            self._github_repo_input.setPlaceholderText("owner/repo")
            integrations_form.addRow("GitHub repo", self._github_repo_input)

            self._obsidian_vault_input = QLineEdit(
                get_integration_setting("obsidian_vault_path"),
                self,
            )
            self._obsidian_vault_input.setPlaceholderText("~/Documents/Obsidian Vault")
            integrations_form.addRow("Obsidian vault path", self._obsidian_vault_input)

            self._notion_page_input = QLineEdit(
                get_integration_setting("notion_updates_page_id"),
                self,
            )
            self._notion_page_input.setPlaceholderText("Notion page id")
            integrations_form.addRow("Notion page id", self._notion_page_input)

            self._github_token_input = QLineEdit(
                get_integration_setting("github_api_token"),
                self,
            )
            self._github_token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._github_token_input.setPlaceholderText("GitHub token (optional)")
            integrations_form.addRow("GitHub token", self._github_token_input)

            self._notion_token_input = QLineEdit(
                get_integration_setting("notion_api_token"),
                self,
            )
            self._notion_token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._notion_token_input.setPlaceholderText("Notion integration token")
            integrations_form.addRow("Notion token", self._notion_token_input)

            self._dictation_target_combo = QComboBox(self)
            self._dictation_target_combo.addItem("В активное поле", "active_field")
            self._dictation_target_combo.addItem("Через API", "api")
            self._select_combo_value(self._dictation_target_combo, widget._dictation_target)
            integrations_form.addRow("Режим диктовки", self._dictation_target_combo)

            self._dictation_api_url_input = QLineEdit(
                get_integration_setting("dictation_api_url"),
                self,
            )
            self._dictation_api_url_input.setPlaceholderText("http://127.0.0.1:8787/v1/dictation")
            integrations_form.addRow("Dictation API URL", self._dictation_api_url_input)

            self._dictation_api_token_input = QLineEdit(
                get_integration_setting("dictation_api_token"),
                self,
            )
            self._dictation_api_token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._dictation_api_token_input.setPlaceholderText("X-API-Key / Bearer token (optional)")
            integrations_form.addRow("Dictation API token", self._dictation_api_token_input)

            integration_actions = QHBoxLayout()
            test_integrations_button = QPushButton("Проверить интеграции", self)
            test_integrations_button.clicked.connect(self._test_integrations)
            integration_actions.addWidget(test_integrations_button)
            integration_actions.addStretch(1)
            integrations_form.addRow("Notion/GitHub", integration_actions)

            memory_actions = QHBoxLayout()
            clear_memory_button = QPushButton("Очистить личную память...", self)
            clear_memory_button.clicked.connect(self._clear_personal_memory)
            memory_actions.addWidget(clear_memory_button)
            memory_actions.addStretch(1)
            integrations_form.addRow("Память о пользователе", memory_actions)

            self._idle_motion_checkbox = QCheckBox("Плавное движение в покое", self)
            self._idle_motion_checkbox.setChecked(widget._idle_motion_enabled)
            self._idle_motion_checkbox.toggled.connect(self._sync_preview)
            appearance_form.addRow(self._idle_motion_checkbox)

            self._snap_checkbox = QCheckBox("Прилипать к краю экрана", self)
            self._snap_checkbox.setChecked(widget._snap_to_edge_enabled)
            behavior_form.addRow(self._snap_checkbox)

            self._start_hidden_checkbox = QCheckBox("Запускать скрытым", self)
            self._start_hidden_checkbox.setChecked(widget._start_hidden)
            behavior_form.addRow(self._start_hidden_checkbox)

            if get_platform_name() == "macos":
                self._autostart_checkbox = QCheckBox("Запускать при входе", self)
                self._autostart_checkbox.setChecked(widget._launch_at_login_enabled)
                behavior_form.addRow(self._autostart_checkbox)
            else:
                self._autostart_checkbox = None

            self._hotkey_input = QLineEdit(widget._activation_hotkey, self)
            behavior_form.addRow("Горячая клавиша", self._hotkey_input)
            self._text_hotkey_input = QLineEdit(widget._text_hotkey, self)
            behavior_form.addRow("Текстовая клавиша", self._text_hotkey_input)

            layout.addWidget(tabs)

            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                self,
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

            if widget._settings_focus == "voice":
                tabs.setCurrentWidget(behavior_tab)
                self._voice_profile_combo.setFocus()


        def apply(self) -> None:
            self._save_integrations()
            self._widget._set_avatar_size(int(self._size_combo.currentData()))
            selected_skin = str(self._skin_combo.currentData())
            selected_pack_skin = _pack_skin_from_combo_value(selected_skin)
            desired_child_mode = self._child_mode_checkbox.isChecked()
            if selected_pack_skin is not None:
                manifest_path = _pack_manifest_path(selected_pack_skin)
                if manifest_path.exists():
                    self._widget._set_avatar_image_path(manifest_path)
                else:
                    log(f"Avatar pack manifest not found: {manifest_path}")
                    self._widget._set_avatar_image_path(None)
                self._widget._avatar_skin = "classic"
                self._widget._auto_child_skin = True
            else:
                if self._active_pack_skin_id() is not None:
                    self._widget._set_avatar_image_path(None)
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
            self._widget._morning_show_enabled = self._morning_show_checkbox.isChecked()
            self._widget._morning_show_city = (
                self._morning_show_city_input.text().strip() or MORNING_SHOW_CITY
            )
            self._widget._morning_show_hour_limit = int(self._morning_show_hour_limit.value())
            self._widget._smart_followup_enabled = self._smart_followup_checkbox.isChecked()
            self._widget._smart_followup_listen_seconds = float(self._smart_followup_seconds.value())
            self._widget._smart_followup_retries = int(self._smart_followup_retries.value())
            self._widget._auto_interrupt_tts_enabled = self._auto_interrupt_checkbox.isChecked()
            self._widget._auto_interrupt_sample_seconds = float(
                self._auto_interrupt_sample_seconds.value()
            )
            self._widget._auto_interrupt_adaptive_enabled = (
                self._auto_interrupt_adaptive_checkbox.isChecked()
            )
            quiet_threshold = float(self._auto_interrupt_quiet_rms.value())
            noisy_threshold = float(self._auto_interrupt_noisy_rms.value())
            if noisy_threshold <= quiet_threshold:
                noisy_threshold = quiet_threshold + 20.0
            self._widget._auto_interrupt_quiet_rms_threshold = quiet_threshold
            self._widget._auto_interrupt_noisy_rms_threshold = noisy_threshold
            self._widget._auto_interrupt_hits_quiet = int(self._auto_interrupt_hits_quiet.value())
            self._widget._auto_interrupt_hits_normal = int(self._auto_interrupt_hits_normal.value())
            self._widget._auto_interrupt_hits_noisy = int(self._auto_interrupt_hits_noisy.value())
            self._widget._agent_routing_profile = str(self._routing_profile_combo.currentData())
            self._widget._chat_prompt_pack_profile = str(self._prompt_pack_profile_combo.currentData())
            self._widget._dictation_target = str(self._dictation_target_combo.currentData())
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
            text_hotkey_value = self._text_hotkey_input.text().strip()
            if text_hotkey_value and text_hotkey_value != self._widget._text_hotkey:
                self._widget._apply_text_hotkey(text_hotkey_value)

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
            for pack_id in _available_pack_skin_ids():
                pretty_name = pack_id.replace("_", " ").title()
                self._skin_combo.addItem(f"{pretty_name} (персонаж)", _pack_skin_combo_value(pack_id))
            self._skin_combo.blockSignals(current_signal_state)
            active_pack_skin_id = self._active_pack_skin_id()
            if active_pack_skin_id is not None:
                resolved_skin = _pack_skin_combo_value(active_pack_skin_id)
            elif selected_skin in _avatar_skin_ids():
                resolved_skin = str(selected_skin)
            else:
                resolved_skin = AVATAR_SKIN
            self._select_combo_value(self._skin_combo, resolved_skin)

        def _active_pack_skin_id(self) -> str | None:
            current_path = self._widget._avatar_path
            if current_path is None:
                return None
            try:
                resolved_current = current_path.resolve()
            except OSError:
                return None
            for pack_id in _available_pack_skin_ids():
                try:
                    if resolved_current == _pack_manifest_path(pack_id).resolve():
                        return pack_id
                except OSError:
                    continue
            return None

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
                "Avatar Files (*.png *.svg *.jpg *.jpeg *.webp *.json *.lottie)",
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
            if not hasattr(self, "_child_mode_checkbox"):
                return
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

        def _sync_auto_interrupt_controls(self) -> None:
            enabled = self._auto_interrupt_adaptive_checkbox.isChecked()
            self._auto_interrupt_quiet_rms.setEnabled(enabled)
            self._auto_interrupt_noisy_rms.setEnabled(enabled)
            self._auto_interrupt_hits_quiet.setEnabled(enabled)
            self._auto_interrupt_hits_normal.setEnabled(enabled)
            self._auto_interrupt_hits_noisy.setEnabled(enabled)

        def _sync_auto_interrupt_thresholds(self) -> None:
            quiet_threshold = float(self._auto_interrupt_quiet_rms.value())
            current_noisy = float(self._auto_interrupt_noisy_rms.value())
            min_noisy = quiet_threshold + 20.0
            if current_noisy < min_noisy:
                was_blocked = self._auto_interrupt_noisy_rms.blockSignals(True)
                self._auto_interrupt_noisy_rms.setValue(min_noisy)
                self._auto_interrupt_noisy_rms.blockSignals(was_blocked)

        def _run_voice_auto_tune(self) -> None:
            current = {
                "smart_followup_enabled": self._smart_followup_checkbox.isChecked(),
                "smart_followup_listen_seconds": float(self._smart_followup_seconds.value()),
                "smart_followup_retries": int(self._smart_followup_retries.value()),
                "auto_interrupt_tts_enabled": self._auto_interrupt_checkbox.isChecked(),
                "auto_interrupt_sample_seconds": float(self._auto_interrupt_sample_seconds.value()),
                "auto_interrupt_adaptive_enabled": self._auto_interrupt_adaptive_checkbox.isChecked(),
                "auto_interrupt_quiet_rms_threshold": float(self._auto_interrupt_quiet_rms.value()),
                "auto_interrupt_noisy_rms_threshold": float(self._auto_interrupt_noisy_rms.value()),
                "auto_interrupt_hits_quiet": int(self._auto_interrupt_hits_quiet.value()),
                "auto_interrupt_hits_normal": int(self._auto_interrupt_hits_normal.value()),
                "auto_interrupt_hits_noisy": int(self._auto_interrupt_hits_noisy.value()),
            }
            plan = build_voice_auto_tune_plan(current=current, limit=40)
            settings = plan.get("settings")
            if not isinstance(settings, dict) or not settings:
                QMessageBox.information(
                    self,
                    "Auto-tune",
                    str(plan.get("summary", "Недостаточно данных для авто-тюнинга.")),
                )
                return

            self._smart_followup_checkbox.setChecked(bool(settings.get("smart_followup_enabled", True)))
            self._smart_followup_seconds.setValue(float(settings.get("smart_followup_listen_seconds", 3.0)))
            self._smart_followup_retries.setValue(int(settings.get("smart_followup_retries", 1)))
            self._auto_interrupt_checkbox.setChecked(bool(settings.get("auto_interrupt_tts_enabled", True)))
            self._auto_interrupt_sample_seconds.setValue(float(settings.get("auto_interrupt_sample_seconds", 1.0)))
            self._auto_interrupt_adaptive_checkbox.setChecked(
                bool(settings.get("auto_interrupt_adaptive_enabled", True))
            )
            self._auto_interrupt_quiet_rms.setValue(
                float(settings.get("auto_interrupt_quiet_rms_threshold", 140.0))
            )
            self._auto_interrupt_noisy_rms.setValue(
                float(settings.get("auto_interrupt_noisy_rms_threshold", 260.0))
            )
            self._auto_interrupt_hits_quiet.setValue(int(settings.get("auto_interrupt_hits_quiet", 1)))
            self._auto_interrupt_hits_normal.setValue(int(settings.get("auto_interrupt_hits_normal", 2)))
            self._auto_interrupt_hits_noisy.setValue(int(settings.get("auto_interrupt_hits_noisy", 3)))
            self._sync_auto_interrupt_thresholds()
            self._sync_auto_interrupt_controls()

            changed = plan.get("changed")
            labels = {
                "smart_followup_enabled": "Умный follow-up",
                "smart_followup_listen_seconds": "Окно дослушивания",
                "smart_followup_retries": "Повторы в follow-up",
                "auto_interrupt_tts_enabled": "Прерывание озвучивания",
                "auto_interrupt_sample_seconds": "Окно barge-in",
                "auto_interrupt_adaptive_enabled": "Адаптивный auto-interrupt",
                "auto_interrupt_quiet_rms_threshold": "Порог тихой среды",
                "auto_interrupt_noisy_rms_threshold": "Порог шумной среды",
                "auto_interrupt_hits_quiet": "Подтверждений (тихо)",
                "auto_interrupt_hits_normal": "Подтверждений (обычно)",
                "auto_interrupt_hits_noisy": "Подтверждений (шумно)",
            }
            if isinstance(changed, dict) and changed:
                changed_lines = []
                for key in changed:
                    label = labels.get(str(key), str(key))
                    changed_lines.append(f"• {label}")
                changed_text = "\n".join(changed_lines[:8])
                text = f"{plan.get('summary', 'Авто-тюнинг применен.')}\n\nИзменено:\n{changed_text}"
            else:
                text = str(plan.get("summary", "Авто-тюнинг завершен."))
            QMessageBox.information(self, "Auto-tune", text)

        def _clear_personal_memory(self) -> None:
            answer = QMessageBox.question(
                self,
                "Очистить личную память",
                "Удалить все сохраненные личные предпочтения и факты о пользователе?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            message = clear_user_profile()
            QMessageBox.information(self, "Личная память", message)

        def _save_integrations(self) -> None:
            save_integration_settings(
                {
                    "obsidian_vault_path": self._obsidian_vault_input.text().strip(),
                    "github_default_repo": self._github_repo_input.text().strip(),
                    "notion_updates_page_id": self._notion_page_input.text().strip(),
                    "github_api_token": self._github_token_input.text().strip(),
                    "notion_api_token": self._notion_token_input.text().strip(),
                    "dictation_api_url": self._dictation_api_url_input.text().strip(),
                    "dictation_api_token": self._dictation_api_token_input.text().strip(),
                }
            )

        def _test_integrations(self) -> None:
            self._save_integrations()
            repo = self._github_repo_input.text().strip()
            page_id = self._notion_page_input.text().strip()

            checks: list[str] = []
            if not repo:
                checks.append("GitHub: укажи repo в формате owner/repo.")
            else:
                since_iso = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
                try:
                    commits = fetch_recent_commits(repo, since_iso=since_iso, limit=1)
                    checks.append(f"GitHub: ok ({len(commits)} recent commits).")
                except GitHubServiceError as exc:
                    checks.append(f"GitHub: ошибка — {exc}")
                except Exception as exc:
                    checks.append(f"GitHub: ошибка — {type(exc).__name__}: {exc}")

            if not page_id:
                checks.append("Notion: укажи page id.")
            else:
                try:
                    lines = read_page_text(page_id, limit=3)
                    checks.append(f"Notion: ok ({len(lines)} text blocks).")
                except NotionServiceError as exc:
                    checks.append(f"Notion: ошибка — {exc}")
                except Exception as exc:
                    checks.append(f"Notion: ошибка — {type(exc).__name__}: {exc}")

            QMessageBox.information(self, "Проверка интеграций", "\n".join(checks))

        def _test_morning_show(self) -> None:
            city = self._morning_show_city_input.text().strip() or MORNING_SHOW_CITY
            hour_limit = int(self._morning_show_hour_limit.value())
            enabled = self._morning_show_checkbox.isChecked()
            preview = get_morning_show_message(
                force=True,
                city=city,
                hour_limit=hour_limit,
                enabled=enabled,
                mark_delivered=False,
            )
            if not preview:
                QMessageBox.information(
                    self,
                    "Утреннее шоу",
                    "Не удалось сформировать утреннее шоу для теста.",
                )
                return
            speak(preview)
            QMessageBox.information(self, "Утреннее шоу (тест)", preview)

        def _reset_morning_show_today(self) -> None:
            reset_morning_show_today()
            QMessageBox.information(
                self,
                "Утреннее шоу",
                "Сбросила отметку показа на сегодня. Следующее обращение снова запустит шоу.",
            )

    class OnboardingDialog(QDialog):
        def __init__(self, widget: "AvatarWidget") -> None:
            super().__init__(widget)
            self.setWindowTitle("Приветствие")
            self.setModal(True)
            self.setMinimumWidth(420)
            self._widget = widget
            self._mic_testing = False
            self._check_state = {
                "settings": False,
                "voice": False,
                "mic": False,
            }
            self.setStyleSheet(_dialog_brand_stylesheet())

            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 18)
            layout.setSpacing(12)

            title = QLabel("Добро пожаловать, я Вася", self)
            title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {BRAND_ACCENT};")
            layout.addWidget(title)

            hotkey_hint = widget._activation_hotkey or HOTKEY_COMBINATION
            text_hotkey_hint = widget._text_hotkey or HOTKEY_TEXT_COMBINATION
            body = QLabel(
                "Я рядом и готов помочь.\n"
                f"Горячая клавиша: {hotkey_hint}\n"
                f"Текстовая клавиша: {text_hotkey_hint}\n"
                "Клик по мне — начать говорить, правый клик — меню.",
                self,
            )
            body.setWordWrap(True)
            body.setStyleSheet(f"color: {BRAND_MUTED};")
            layout.addWidget(body)

            self._mic_status = QLabel("Можно сразу проверить микрофон.", self)
            self._mic_status.setWordWrap(True)
            self._mic_status.setStyleSheet(f"color: {BRAND_MUTED}; font-size: 12px;")
            layout.addWidget(self._mic_status)

            checklist_title = QLabel("Быстрый чеклист", self)
            checklist_title.setStyleSheet(f"font-size: 12px; color: {BRAND_MUTED}; font-weight: 600;")
            layout.addWidget(checklist_title)

            self._check_settings = QLabel(self._format_check_text("pending", "Открыть настройки"), self)
            self._check_voice = QLabel(self._format_check_text("pending", "Выбрать голос"), self)
            self._check_mic = QLabel(self._format_check_text("pending", "Проверить микрофон"), self)
            for item in (self._check_settings, self._check_voice, self._check_mic):
                item.setStyleSheet(f"color: {BRAND_TEXT}; font-size: 12px;")
                layout.addWidget(item)

            self._progress_label = QLabel("Готовность: 0/3", self)
            self._progress_label.setStyleSheet(f"color: {BRAND_MUTED}; font-size: 12px;")
            layout.addWidget(self._progress_label)
            self._progress_bar = QProgressBar(self)
            self._progress_bar.setRange(0, 3)
            self._progress_bar.setValue(0)
            self._progress_bar.setTextVisible(False)
            self._progress_bar.setFixedHeight(6)
            self._progress_bar.setStyleSheet(
                """
                QProgressBar {
                    background: #121c47;
                    border: 1px solid #3d61c9;
                    border-radius: 4px;
                }
                QProgressBar::chunk {
                    background: #22b8ff;
                    border-radius: 4px;
                }
                """
            )
            layout.addWidget(self._progress_bar)

            button_row = QHBoxLayout()
            button_row.setSpacing(10)
            settings_button = QPushButton("Настройки", self)
            settings_button.clicked.connect(self._open_settings)
            voice_button = QPushButton("Голос", self)
            voice_button.clicked.connect(self._open_voice_settings)
            mic_button = QPushButton("Тест микрофона", self)
            mic_button.clicked.connect(self._run_mic_test)
            close_button = QPushButton("Готово", self)
            close_button.clicked.connect(self.accept)

            button_row.addWidget(settings_button)
            button_row.addWidget(voice_button)
            button_row.addWidget(mic_button)
            button_row.addStretch(1)
            button_row.addWidget(close_button)
            layout.addLayout(button_row)

        def _open_settings(self) -> None:
            self._widget._open_settings_dialog()
            self._mark_check("settings", True)

        def _open_voice_settings(self) -> None:
            self._widget._open_settings_dialog(focus="voice")
            self._mark_check("voice", True)

        def _run_mic_test(self) -> None:
            if self._mic_testing:
                return
            self._mic_testing = True
            self._mic_status.setText("Слушаю 2 секунды…")

            def worker():
                ok, message = _run_mic_health_check(2.0)

                def finish():
                    self._mic_status.setText(message)
                    self._mic_testing = False
                    self._mark_check("mic", ok)

                QTimer.singleShot(0, finish)

            threading.Thread(target=worker, daemon=True).start()

        def _mark_check(self, key: str, ok: bool) -> None:
            self._check_state[key] = ok
            state = "done" if ok else "warn"
            if key == "settings":
                self._check_settings.setText(self._format_check_text(state, "Открыть настройки"))
            elif key == "voice":
                self._check_voice.setText(self._format_check_text(state, "Выбрать голос"))
            elif key == "mic":
                self._check_mic.setText(self._format_check_text(state, "Проверить микрофон"))
            self._update_progress()

        def _update_progress(self) -> None:
            done = sum(1 for value in self._check_state.values() if value)
            self._progress_label.setText(f"Готовность: {done}/3")
            self._progress_bar.setValue(done)

        @staticmethod
        def _format_check_text(state: str, label: str) -> str:
            colors = {
                "done": "#6ee7a8",
                "warn": "#ffb347",
                "pending": "#7a8bb8",
            }
            color = colors.get(state, "#7a8bb8")
            dot = f"<span style='color:{color}'>●</span>"
            return f"{dot} {label}"

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
            self._morning_show_enabled = bool(
                self._widget_state.get("morning_show_enabled", MORNING_SHOW_ENABLED)
            )
            self._morning_show_city = str(
                self._widget_state.get("morning_show_city", MORNING_SHOW_CITY)
            ).strip() or MORNING_SHOW_CITY
            raw_hour_limit = self._widget_state.get(
                "morning_show_hour_limit",
                MORNING_SHOW_HOUR_LIMIT,
            )
            try:
                self._morning_show_hour_limit = int(raw_hour_limit)
            except (TypeError, ValueError):
                self._morning_show_hour_limit = int(MORNING_SHOW_HOUR_LIMIT)
            self._morning_show_hour_limit = min(23, max(0, self._morning_show_hour_limit))
            self._smart_followup_enabled = bool(
                self._widget_state.get(
                    "smart_followup_enabled",
                    VOICE_SMART_FOLLOWUP_ENABLED,
                )
            )
            raw_followup_seconds = self._widget_state.get(
                "smart_followup_listen_seconds",
                VOICE_SMART_FOLLOWUP_LISTEN_SECONDS,
            )
            try:
                self._smart_followup_listen_seconds = float(raw_followup_seconds)
            except (TypeError, ValueError):
                self._smart_followup_listen_seconds = float(VOICE_SMART_FOLLOWUP_LISTEN_SECONDS)
            self._smart_followup_listen_seconds = min(8.0, max(1.0, self._smart_followup_listen_seconds))
            raw_followup_retries = self._widget_state.get(
                "smart_followup_retries",
                VOICE_SMART_FOLLOWUP_RETRIES,
            )
            try:
                self._smart_followup_retries = int(raw_followup_retries)
            except (TypeError, ValueError):
                self._smart_followup_retries = int(VOICE_SMART_FOLLOWUP_RETRIES)
            self._smart_followup_retries = min(3, max(1, self._smart_followup_retries))
            self._auto_interrupt_tts_enabled = bool(
                self._widget_state.get(
                    "auto_interrupt_tts_enabled",
                    VOICE_AUTO_INTERRUPT_TTS_ENABLED,
                )
            )
            raw_auto_interrupt_sample = self._widget_state.get(
                "auto_interrupt_sample_seconds",
                VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS,
            )
            try:
                self._auto_interrupt_sample_seconds = float(raw_auto_interrupt_sample)
            except (TypeError, ValueError):
                self._auto_interrupt_sample_seconds = float(VOICE_AUTO_INTERRUPT_SAMPLE_SECONDS)
            self._auto_interrupt_sample_seconds = min(3.0, max(0.5, self._auto_interrupt_sample_seconds))
            self._auto_interrupt_adaptive_enabled = bool(
                self._widget_state.get(
                    "auto_interrupt_adaptive_enabled",
                    VOICE_AUTO_INTERRUPT_ADAPTIVE_ENABLED,
                )
            )
            raw_auto_interrupt_quiet_rms = self._widget_state.get(
                "auto_interrupt_quiet_rms_threshold",
                VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD,
            )
            raw_auto_interrupt_noisy_rms = self._widget_state.get(
                "auto_interrupt_noisy_rms_threshold",
                VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD,
            )
            try:
                self._auto_interrupt_quiet_rms_threshold = float(raw_auto_interrupt_quiet_rms)
            except (TypeError, ValueError):
                self._auto_interrupt_quiet_rms_threshold = float(VOICE_AUTO_INTERRUPT_QUIET_RMS_THRESHOLD)
            try:
                self._auto_interrupt_noisy_rms_threshold = float(raw_auto_interrupt_noisy_rms)
            except (TypeError, ValueError):
                self._auto_interrupt_noisy_rms_threshold = float(VOICE_AUTO_INTERRUPT_NOISY_RMS_THRESHOLD)
            self._auto_interrupt_quiet_rms_threshold = max(50.0, self._auto_interrupt_quiet_rms_threshold)
            self._auto_interrupt_noisy_rms_threshold = max(
                self._auto_interrupt_quiet_rms_threshold + 20.0,
                self._auto_interrupt_noisy_rms_threshold,
            )
            raw_auto_interrupt_hits_quiet = self._widget_state.get(
                "auto_interrupt_hits_quiet",
                VOICE_AUTO_INTERRUPT_HITS_QUIET,
            )
            raw_auto_interrupt_hits_normal = self._widget_state.get(
                "auto_interrupt_hits_normal",
                VOICE_AUTO_INTERRUPT_HITS_NORMAL,
            )
            raw_auto_interrupt_hits_noisy = self._widget_state.get(
                "auto_interrupt_hits_noisy",
                VOICE_AUTO_INTERRUPT_HITS_NOISY,
            )
            try:
                self._auto_interrupt_hits_quiet = int(raw_auto_interrupt_hits_quiet)
            except (TypeError, ValueError):
                self._auto_interrupt_hits_quiet = int(VOICE_AUTO_INTERRUPT_HITS_QUIET)
            try:
                self._auto_interrupt_hits_normal = int(raw_auto_interrupt_hits_normal)
            except (TypeError, ValueError):
                self._auto_interrupt_hits_normal = int(VOICE_AUTO_INTERRUPT_HITS_NORMAL)
            try:
                self._auto_interrupt_hits_noisy = int(raw_auto_interrupt_hits_noisy)
            except (TypeError, ValueError):
                self._auto_interrupt_hits_noisy = int(VOICE_AUTO_INTERRUPT_HITS_NOISY)
            self._auto_interrupt_hits_quiet = min(6, max(1, self._auto_interrupt_hits_quiet))
            self._auto_interrupt_hits_normal = min(6, max(1, self._auto_interrupt_hits_normal))
            self._auto_interrupt_hits_noisy = min(6, max(1, self._auto_interrupt_hits_noisy))
            self._agent_routing_profile = str(
                self._widget_state.get("agent_routing_profile", AGENT_ROUTING_PROFILE)
            ).strip() or AGENT_ROUTING_PROFILE
            self._chat_prompt_pack_profile = str(
                self._widget_state.get("chat_prompt_pack_profile", CHAT_PROMPT_PACK_PROFILE)
            ).strip() or CHAT_PROMPT_PACK_PROFILE
            self._dictation_target = str(
                self._widget_state.get("dictation_target", "active_field")
            ).strip() or "active_field"
            if self._dictation_target not in {"active_field", "api"}:
                self._dictation_target = "active_field"
            self._launch_at_login_enabled = is_autostart_enabled()
            self._activation_hotkey = str(
                self._widget_state.get("hotkey_combination", HOTKEY_COMBINATION)
            )
            self._text_hotkey = str(
                self._widget_state.get("text_hotkey_combination", HOTKEY_TEXT_COMBINATION)
            )
            self.setFixedSize(self._avatar_size, self._avatar_size)

            self._drag_pos: QPoint | None = None
            self._press_pos: QPoint | None = None
            self._interaction_lock = threading.Lock()
            self._interaction_control_lock = threading.Lock()
            self._queued_voice_activation = False
            self._text_command_control_lock = threading.Lock()
            self._text_command_cancel_event: threading.Event | None = None
            self._queued_text_command: str | None = None
            self._state = assistant_state.get()
            self._pending_speaking_state: AssistantState | None = None
            self._pulse = 0.0
            self._bob = 0.0
            self._smile_bounce = 0.0
            self._avatar_path = self._resolve_avatar_path()
            self._avatar_is_pack = False
            self._avatar_pack_frames: dict[str, list[QPixmap]] = {}
            self._avatar_pack_timing_ms: dict[str, int] = {}
            self._avatar_pack_frame_index: dict[str, int] = {}
            self._avatar_pack_elapsed_ms = 0.0
            self._avatar_pack_preloaded_cache: dict[str, dict[str, object]] = {}
            self._avatar_lottie = None
            self._avatar_lottie_total_frames = 0
            self._avatar_lottie_frame = 0.0
            self._avatar_lottie_fps = 30.0
            self._avatar = self._load_avatar()
            self._avatar_is_svg = (
                self._avatar_path is not None and self._avatar_path.suffix.lower() == ".svg"
            )
            self._avatar_is_lottie = (
                self._avatar_path is not None
                and self._avatar_path.suffix.lower() in {".json", ".lottie"}
                and not self._avatar_is_pack
            )
            self._tray_icon_pixmap = self._build_tray_pixmap()
            self._bridge = StateBridge()
            self._bubble = ResponseBubble()
            self._hover_bubble = HoverBubble()
            self._hotkey_listener = None
            self._tray = None
            self._allow_close = False
            self._last_effective_skin = self._effective_avatar_skin()
            self._settings_focus: str | None = None
            self._hover_hint_active = False
            self._state_since = time.monotonic()
            self._voice_health_cached_text = "Скорость: пока нет данных"
            self._voice_health_cached_at = 0.0

            self._bridge.state_changed.connect(self._apply_state)
            self._bridge.exit_requested.connect(self.quit_application)
            self._bridge.text_command_requested.connect(self._open_text_command_dialog)
            assistant_state.subscribe(self._on_state_changed)

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(60)

            self._restore_position()
            self._update_bubble()
            self._start_hotkey_listener()
            self._setup_tray()
            self._maybe_run_onboarding()
            self._preload_avatar_packs()
            if VOICE_RUNTIME_PREWARM_ON_WIDGET_START:
                start_runtime_prewarm_async()
            start_memory_background_scheduler()

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
            suffix = path.suffix.lower()
            if suffix == ".svg":
                return self._render_svg_avatar(512)
            if suffix in {".json", ".lottie"}:
                if suffix == ".json" and self._load_avatar_pack(path):
                    return self._render_pack_avatar(512, state_key="idle")
                return self._load_lottie_avatar(path)
            pixmap = QPixmap(str(path))
            return pixmap if not pixmap.isNull() else None

        def _load_avatar_pack(self, manifest_path: Path) -> bool:
            self._avatar_is_pack = False
            self._avatar_pack_frames = {}
            self._avatar_pack_timing_ms = {}
            self._avatar_pack_frame_index = {}
            self._avatar_pack_elapsed_ms = 0.0
            manifest_key = str(manifest_path.resolve())
            cached_payload = self._avatar_pack_preloaded_cache.get(manifest_key)
            if isinstance(cached_payload, dict):
                cached_frames = cached_payload.get("frames")
                cached_timing = cached_payload.get("timing_ms")
                if isinstance(cached_frames, dict) and isinstance(cached_timing, dict):
                    self._avatar_pack_frames = {
                        str(key): list(value)
                        for key, value in cached_frames.items()
                        if isinstance(value, list) and value
                    }
                    self._avatar_pack_timing_ms = {
                        str(key): int(value)
                        for key, value in cached_timing.items()
                    }
                    for key, frames in self._avatar_pack_frames.items():
                        if frames:
                            self._avatar_pack_frame_index[key] = 0
                    if self._avatar_pack_frames:
                        self._avatar_is_pack = True
                        return True
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return False
            if not isinstance(payload, dict):
                return False
            raw_states = payload.get("states")
            if not isinstance(raw_states, dict):
                return False

            base_dir = manifest_path.parent
            loaded_any = False
            for key, value in raw_states.items():
                state_key = str(key).strip().lower()
                if state_key not in {"idle", "listening", "thinking", "speaking", "error"}:
                    continue
                if not isinstance(value, list):
                    continue
                frames: list[QPixmap] = []
                for item in value:
                    candidate = base_dir / str(item).strip()
                    pixmap = QPixmap(str(candidate))
                    if pixmap.isNull():
                        continue
                    frames.append(pixmap)
                if frames:
                    self._avatar_pack_frames[state_key] = frames
                    self._avatar_pack_frame_index[state_key] = 0
                    loaded_any = True

            if not loaded_any:
                return False

            timing_defaults = {
                "idle": 260,
                "listening": 180,
                "thinking": 200,
                "speaking": 90,
                "error": 150,
            }
            raw_timing = payload.get("timing_ms")
            if isinstance(raw_timing, dict):
                for key, default_value in timing_defaults.items():
                    raw_value = raw_timing.get(key, default_value)
                    try:
                        self._avatar_pack_timing_ms[key] = min(2000, max(40, int(raw_value)))
                    except (TypeError, ValueError):
                        self._avatar_pack_timing_ms[key] = default_value
            else:
                self._avatar_pack_timing_ms = dict(timing_defaults)

            self._avatar_pack_preloaded_cache[manifest_key] = {
                "frames": {key: list(value) for key, value in self._avatar_pack_frames.items()},
                "timing_ms": dict(self._avatar_pack_timing_ms),
            }
            self._avatar_is_pack = True
            return True

        def _preload_avatar_packs(self) -> None:
            for pack_id in _available_pack_skin_ids():
                manifest_path = _pack_manifest_path(pack_id)
                if not manifest_path.exists():
                    continue
                manifest_key = str(manifest_path.resolve())
                if manifest_key in self._avatar_pack_preloaded_cache:
                    continue
                snapshot = (
                    self._avatar_is_pack,
                    self._avatar_pack_frames,
                    self._avatar_pack_timing_ms,
                    self._avatar_pack_frame_index,
                    self._avatar_pack_elapsed_ms,
                )
                try:
                    _ = self._load_avatar_pack(manifest_path)
                except Exception as exc:
                    log(f"Failed to preload avatar pack {pack_id}: {exc}")
                finally:
                    (
                        self._avatar_is_pack,
                        self._avatar_pack_frames,
                        self._avatar_pack_timing_ms,
                        self._avatar_pack_frame_index,
                        self._avatar_pack_elapsed_ms,
                    ) = snapshot

        def _load_lottie_avatar(self, path: Path):
            if LottieAnimation is None:
                log(
                    "Lottie avatar selected, but rlottie-python is not installed. "
                    "Run: .venv/bin/pip install rlottie-python"
                )
                return None
            try:
                animation = LottieAnimation.from_file(str(path))
            except Exception as exc:
                log(f"Failed to load lottie avatar {path}: {exc}")
                return None
            if not animation:
                return None
            try:
                total_frames = int(animation.lottie_animation_get_totalframe())
            except Exception:
                total_frames = 1
            try:
                duration = float(animation.lottie_animation_get_duration())
                fps = (total_frames / duration) if duration > 0 else 30.0
            except Exception:
                fps = 30.0
            self._avatar_lottie = animation
            self._avatar_lottie_total_frames = max(1, total_frames)
            self._avatar_lottie_frame = 0.0
            self._avatar_lottie_fps = min(90.0, max(8.0, fps))
            return self._render_lottie_avatar(512)

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
            if (
                self._pending_speaking_state is not None
                and previous_state == AssistantStateName.IDLE
                and state.name == AssistantStateName.SPEAKING
            ):
                self._pending_speaking_state = state
                return
            if (
                previous_state == AssistantStateName.THINKING
                and state.name == AssistantStateName.SPEAKING
                and self._pending_speaking_state is None
            ):
                self._pending_speaking_state = state
                self._state = AssistantState(AssistantStateName.IDLE, state.text)
                self._update_bubble()
                self._update_tray_tooltip()
                self.update()
                QTimer.singleShot(180, self._flush_pending_speaking_state)
                return
            state_changed = previous_state != state.name
            self._state = state
            self._pending_speaking_state = None
            if state_changed:
                self._state_since = time.monotonic()
            if previous_state == AssistantStateName.SPEAKING and state.name == AssistantStateName.IDLE:
                self._smile_bounce = 1.0
            self._update_bubble()
            self._update_tray_tooltip()
            self.update()
            if self._hover_hint_active:
                self._refresh_hover_hint()

        def _flush_pending_speaking_state(self) -> None:
            pending_state = self._pending_speaking_state
            if pending_state is None:
                return
            self._pending_speaking_state = None
            # Не переигрываем speaking, если за это время ассистент уже ушел в другой state.
            if assistant_state.get().name != AssistantStateName.SPEAKING:
                return
            self._apply_state(pending_state)

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
            if self._avatar_is_pack and self._avatar_pack_frames:
                self._avatar_pack_elapsed_ms += 60.0
                state_key = self._avatar_state_key(self._state.name)
                state_frames = self._avatar_pack_frames.get(state_key) or self._avatar_pack_frames.get("idle") or []
                frame_count = len(state_frames)
                interval_ms = int(self._avatar_pack_timing_ms.get(state_key, 220))
                if frame_count > 1 and self._avatar_pack_elapsed_ms >= interval_ms:
                    self._avatar_pack_elapsed_ms = 0.0
                    current_index = self._avatar_pack_frame_index.get(state_key, 0)
                    self._avatar_pack_frame_index[state_key] = (current_index + 1) % frame_count
            if self._avatar_is_lottie and self._avatar_lottie is not None and self._avatar_lottie_total_frames > 1:
                frame_step = max(0.1, self._avatar_lottie_fps * 0.06)
                self._avatar_lottie_frame = (
                    self._avatar_lottie_frame + frame_step
                ) % self._avatar_lottie_total_frames
            self.update()
            self._update_bubble_position()
            self._update_hover_bubble_position()

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

        def enterEvent(self, event) -> None:
            _ = event
            self._show_hover_hint()
            super().enterEvent(event)

        def leaveEvent(self, event) -> None:
            _ = event
            self._hide_hover_hint()
            super().leaveEvent(event)

        def contextMenuEvent(self, event) -> None:
            try:
                menu = QMenu(self)

                toggle_action = menu.addAction(
                    "Скрыть Васю" if self.isVisible() else "Показать Васю"
                )
                menu.addSeparator()
                interaction_menu = menu.addMenu("Общение")
                listen_action = interaction_menu.addAction("Начать слушать")
                text_action = interaction_menu.addAction("Текстовая команда...")
                quick_action = interaction_menu.addAction("Быстрые команды")
                mic_test_action = interaction_menu.addAction("Тест микрофона")

                memory_menu = menu.addMenu("Memory Center")
                memory_status_action = memory_menu.addAction("Статус памяти...")
                memory_sync_action = memory_menu.addAction("Синхронизировать память")

                settings_menu = menu.addMenu("Настройки")
                settings_action = settings_menu.addAction("Открыть настройки...")
                clear_memory_action = settings_menu.addAction("Очистить личную память...")
                menu.addSeparator()
                quit_action = menu.addAction("Закрыть Васю")

                chosen_action = menu.exec(event.globalPos())
                if chosen_action is None:
                    return

                handlers = {
                    toggle_action: self.toggle_avatar_visibility,
                    listen_action: self._activate_interaction,
                    text_action: self._open_text_command_dialog,
                    quick_action: self._open_quick_commands,
                    mic_test_action: self._run_quick_mic_test,
                    memory_status_action: self._show_memory_center_status,
                    memory_sync_action: self._sync_memory_center_now,
                    settings_action: self._open_settings_dialog,
                    clear_memory_action: self._clear_personal_memory,
                    quit_action: self.quit_application,
                }
                handler = handlers.get(chosen_action)
                if handler is not None:
                    handler()
            except Exception as exc:
                log(f"Context menu error: {exc}")

        def _activate_interaction(self) -> None:
            if self._interaction_lock.locked():
                if assistant_state.get().name == AssistantStateName.SPEAKING:
                    log_voice_event("widget_activation_interrupt_speaking")
                    stop_speaking()
                    assistant_state.set(
                        AssistantStateName.IDLE,
                        "Остановила озвучивание. Нажми еще раз, чтобы говорить.",
                    )
                    return
                else:
                    with self._interaction_control_lock:
                        self._queued_voice_activation = True
                    log_voice_event("widget_activation_queued reason=interaction_in_progress")
                    assistant_state.set(
                        AssistantStateName.THINKING,
                        "Заканчиваю текущий запрос и сразу начну слушать.",
                    )
                    return

            self._start_interaction_thread("widget_activation_started")

        def _start_interaction_thread(self, log_event: str) -> None:
            def worker() -> None:
                with self._interaction_lock:
                    try:
                        log_voice_event(log_event)
                        action = run_voice_interaction()
                    except Exception as exc:
                        log(f"Voice interaction failed: {exc}")
                        assistant_state.set(
                            AssistantStateName.ERROR,
                            f"Ошибка голосового контура: {type(exc).__name__}",
                        )
                        return
                    if action == AssistantControlAction.EXIT:
                        self._bridge.exit_requested.emit()
                    elif action == AssistantControlAction.OPEN_TEXT_COMMAND:
                        self._bridge.text_command_requested.emit()
                with self._interaction_control_lock:
                    queued_activation = self._queued_voice_activation
                    self._queued_voice_activation = False
                if queued_activation and action != AssistantControlAction.EXIT:
                    QTimer.singleShot(
                        0,
                        lambda: self._start_interaction_thread("widget_activation_auto_queued"),
                    )

            threading.Thread(target=worker, daemon=True).start()

        def closeEvent(self, event) -> None:
            if not self._allow_close:
                event.ignore()
                self.hide_avatar()
                return

            self._save_position()
            self._bubble.close()
            self._hover_bubble.close()
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

            if self._avatar is not None or self._avatar_is_lottie or self._avatar_is_pack:
                self._paint_ambient_glow(painter)
                self._paint_avatar(painter)
            else:
                self._paint_character(painter)
            self._paint_status_indicator(painter)

        def _paint_status_indicator(self, painter: QPainter) -> None:
            if self._state.name == AssistantStateName.IDLE:
                return
            painter.save()
            color = _animated_glow(
                self._state.name,
                self._pulse,
                self._effective_avatar_skin(),
            )
            color.setAlpha(220)
            painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
            painter.setBrush(color)
            radius = 6
            x = self.width() - 16
            y = 10
            painter.drawEllipse(QRectF(x, y, radius * 2, radius * 2))
            painter.restore()

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

            self._avatar_lottie = None
            self._avatar_lottie_total_frames = 0
            self._avatar_lottie_frame = 0.0
            self._avatar_lottie_fps = 30.0
            self._avatar_is_pack = False
            self._avatar_pack_frames = {}
            self._avatar_pack_timing_ms = {}
            self._avatar_pack_frame_index = {}
            self._avatar_pack_elapsed_ms = 0.0
            self._avatar = self._load_avatar()
            self._avatar_is_svg = (
                self._avatar_path is not None and self._avatar_path.suffix.lower() == ".svg"
            )
            self._avatar_is_lottie = (
                self._avatar_path is not None
                and self._avatar_path.suffix.lower() in {".json", ".lottie"}
                and not self._avatar_is_pack
            )
            self._tray_icon_pixmap = self._build_tray_pixmap()
            if self._tray is not None:
                self._tray.setIcon(QIcon(self._tray_icon_pixmap))
            self.update()
            self._save_position()

        def _prepare_avatar_pixmap(self, width: int, height: int) -> QPixmap:
            if self._avatar_path is None:
                return QPixmap()

            if self._avatar_is_pack:
                state_key = self._avatar_state_key(self._state.name)
                return self._render_pack_avatar(max(width, height), state_key=state_key)

            if self._avatar_is_lottie:
                return self._render_lottie_avatar(max(width, height))

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

        @staticmethod
        def _avatar_state_key(state_name: AssistantStateName) -> str:
            if state_name == AssistantStateName.LISTENING:
                return "listening"
            if state_name == AssistantStateName.THINKING:
                return "thinking"
            if state_name == AssistantStateName.SPEAKING:
                return "speaking"
            if state_name == AssistantStateName.ERROR:
                return "error"
            return "idle"

        def _render_pack_avatar(self, size: int, *, state_key: str) -> QPixmap:
            frames = self._avatar_pack_frames.get(state_key) or self._avatar_pack_frames.get("idle") or []
            if not frames:
                return QPixmap()
            current_index = self._avatar_pack_frame_index.get(state_key, 0)
            source = frames[current_index % len(frames)]
            target = max(64, int(size))
            return source.scaled(
                target,
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        def _render_lottie_avatar(self, size: int) -> QPixmap:
            if self._avatar_lottie is None:
                return QPixmap()
            render_size = max(64, int(size))
            try:
                frame_index = int(self._avatar_lottie_frame) % max(1, self._avatar_lottie_total_frames)
                raw = self._avatar_lottie.lottie_animation_render(
                    frame_num=frame_index,
                    width=render_size,
                    height=render_size,
                )
            except Exception as exc:
                log(f"Failed to render lottie avatar frame: {exc}")
                return QPixmap()
            image = QImage(raw, render_size, render_size, render_size * 4, QImage.Format.Format_ARGB32)
            if image.isNull():
                return QPixmap()
            return QPixmap.fromImage(image.copy())

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

        def _show_hover_hint(self) -> None:
            if not self.isVisible():
                return
            if self._bubble.isVisible():
                return
            self._hover_hint_active = True
            self._hover_bubble.set_text(self._hover_hint_text())
            self._update_hover_bubble_position()
            self._hover_bubble.show()
            self._hover_bubble.raise_()

        def _refresh_hover_hint(self) -> None:
            if not self._hover_hint_active or not self._hover_bubble.isVisible():
                return
            self._hover_bubble.set_text(self._hover_hint_text())
            self._update_hover_bubble_position()

        def _hide_hover_hint(self) -> None:
            if not self._hover_hint_active:
                return
            self._hover_hint_active = False
            self._hover_bubble.hide()

        def _hover_hint_text(self) -> str:
            if self._state.name == AssistantStateName.LISTENING:
                return "Слушаю…"
            if self._state.name == AssistantStateName.THINKING:
                seconds = max(1, int(time.monotonic() - self._state_since))
                return f"Думаю… {seconds}с"
            if self._state.name == AssistantStateName.SPEAKING:
                return "Говорю…"
            if self._state.name == AssistantStateName.ERROR:
                message = (self._state.message or "").lower()
                if "тихо" in message:
                    return "Слишком тихо — скажи громче"
                if "не расслыш" in message:
                    return "Не расслышал — повтори"
                if "сомнева" in message:
                    return "Сомневаюсь — повтори"
                return "Не понял — повтори"
            return f"Клик — говорить • ПКМ — меню\n{self._voice_health_hint()}"

        def _voice_health_hint(self) -> str:
            now = time.monotonic()
            if (now - self._voice_health_cached_at) < 12.0 and self._voice_health_cached_text:
                return self._voice_health_cached_text
            try:
                hint = build_voice_health_snapshot(limit=24)
            except Exception:
                hint = "Скорость: нет данных"
            self._voice_health_cached_text = " ".join(str(hint).split())
            self._voice_health_cached_at = now
            return self._voice_health_cached_text

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

        def _update_hover_bubble_position(self) -> None:
            if not self._hover_bubble.isVisible():
                return
            bubble_x = self.x() + self.width() + 10
            bubble_y = self.y() + 10
            primary = QGuiApplication.primaryScreen()
            if primary is not None:
                available = primary.availableGeometry()
                if bubble_x + self._hover_bubble.width() > available.right() - 8:
                    bubble_x = self.x() - self._hover_bubble.width() - 10
            self._hover_bubble.move(bubble_x, bubble_y)

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
                    "text_hotkey_combination": self._text_hotkey,
                    "show_response_bubble": self._show_response_bubble,
                    "idle_motion_enabled": self._idle_motion_enabled,
                    "snap_to_edge_enabled": self._snap_to_edge_enabled,
                    "avatar_opacity": self._avatar_opacity,
                    "avatar_skin": self._avatar_skin,
                    "auto_child_skin": self._auto_child_skin,
                    "start_hidden": not self.isVisible(),
                    "morning_show_enabled": self._morning_show_enabled,
                    "morning_show_city": self._morning_show_city,
                    "morning_show_hour_limit": self._morning_show_hour_limit,
                    "smart_followup_enabled": self._smart_followup_enabled,
                    "smart_followup_listen_seconds": self._smart_followup_listen_seconds,
                    "smart_followup_retries": self._smart_followup_retries,
                    "auto_interrupt_tts_enabled": self._auto_interrupt_tts_enabled,
                    "auto_interrupt_sample_seconds": self._auto_interrupt_sample_seconds,
                    "auto_interrupt_adaptive_enabled": self._auto_interrupt_adaptive_enabled,
                    "auto_interrupt_quiet_rms_threshold": self._auto_interrupt_quiet_rms_threshold,
                    "auto_interrupt_noisy_rms_threshold": self._auto_interrupt_noisy_rms_threshold,
                    "auto_interrupt_hits_quiet": self._auto_interrupt_hits_quiet,
                    "auto_interrupt_hits_normal": self._auto_interrupt_hits_normal,
                    "auto_interrupt_hits_noisy": self._auto_interrupt_hits_noisy,
                    "agent_routing_profile": self._agent_routing_profile,
                    "chat_prompt_pack_profile": self._chat_prompt_pack_profile,
                    "dictation_target": self._dictation_target,
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
            text_hotkey = normalize_hotkey_combination(self._text_hotkey)
            exit_hotkey = normalize_hotkey_combination(HOTKEY_EXIT_COMBINATION)
            hotkeys = {
                activation_hotkey: self._activate_interaction,
                text_hotkey: self._request_open_text_command_dialog,
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
                f"Text: {text_hotkey}. Exit: {exit_hotkey}."
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

            text_action = QAction("Текстовая команда...", self)
            text_action.triggered.connect(self._open_text_command_dialog)
            menu.addAction(text_action)

            quick_action = QAction("Быстрые команды", self)
            quick_action.triggered.connect(self._open_quick_commands)
            menu.addAction(quick_action)

            mic_test_action = QAction("Тест микрофона", self)
            mic_test_action.triggered.connect(self._run_quick_mic_test)
            menu.addAction(mic_test_action)

            diagnostics_action = QAction("Диагностика скорости...", self)
            diagnostics_action.triggered.connect(self._show_speed_diagnostics)
            menu.addAction(diagnostics_action)

            memory_status_action = QAction("Memory Center...", self)
            memory_status_action.triggered.connect(self._show_memory_center_status)
            menu.addAction(memory_status_action)

            memory_sync_action = QAction("Синхронизировать память", self)
            memory_sync_action.triggered.connect(self._sync_memory_center_now)
            menu.addAction(memory_sync_action)

            settings_action = QAction("Настройки...", self)
            settings_action.triggered.connect(self._open_settings_dialog)
            menu.addAction(settings_action)

            clear_memory_action = QAction("Очистить личную память...", self)
            clear_memory_action.triggered.connect(self._clear_personal_memory)
            menu.addAction(clear_memory_action)
            menu.addSeparator()

            quit_action = QAction("Закрыть Васю", self)
            quit_action.triggered.connect(self.quit_application)
            menu.addAction(quit_action)

            self._tray.setContextMenu(menu)
            self._tray.activated.connect(self._on_tray_activated)
            self._tray.show()
            self._update_tray_tooltip()

        def _clear_personal_memory(self) -> None:
            answer = QMessageBox.question(
                self,
                "Очистить личную память",
                "Удалить все сохраненные личные предпочтения и факты о пользователе?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            message = clear_user_profile()
            QMessageBox.information(self, "Личная память", message)

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
                if self._state.name == AssistantStateName.THINKING:
                    seconds = max(1, int(time.monotonic() - self._state_since))
                    suffix = f"{suffix} {seconds}с"
                elif self._state.message:
                    detail = " ".join(self._state.message.split())
                    if len(detail) > 56:
                        detail = f"{detail[:53]}..."
                    suffix = f"{suffix} • {detail}"
            else:
                suffix = f" • {self._voice_health_hint()}"
            self._tray.setToolTip(f"Вася AI{suffix}")

        def _open_settings_dialog(self, *, focus: str | None = None) -> None:
            self._settings_focus = focus
            dialog = SettingsDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    dialog.apply()
                except Exception as exc:
                    log(f"Failed to apply settings: {exc}")
            self._settings_focus = None

        def _open_quick_commands(self) -> None:
            dialog = QuickCommandsDialog(self)
            dialog.exec()

        def _show_speed_diagnostics(self) -> None:
            snapshot = build_voice_health_snapshot(limit=24)
            report = build_voice_speed_report(limit=24)
            hints = build_voice_tuning_hints(limit=24)
            text = (
                f"{snapshot}\n\n"
                f"{report}\n\n"
                f"Рекомендации:\n{hints}"
            )
            QMessageBox.information(self, "Диагностика скорости", text)

        def _show_memory_center_status(self) -> None:
            try:
                status = get_memory_center_status()
                text = build_memory_center_summary(status)
            except Exception as exc:
                text = f"Не удалось прочитать Memory Center: {exc}"
            QMessageBox.information(self, "Memory Center", text)

        def _sync_memory_center_now(self) -> None:
            if self._interaction_lock.locked():
                QMessageBox.information(
                    self,
                    "Memory Center",
                    "Сначала дождись завершения текущего запроса.",
                )
                return

            assistant_state.set(AssistantStateName.THINKING, "Синхронизирую Memory Center...")

            def worker() -> None:
                try:
                    result = sync_memory_source("all", force=True)
                    ingested = int(result.get("ingested", 0))
                    ok = bool(result.get("ok"))
                    if ok:
                        successful = ", ".join(result.get("successful_sources", [])) or "нет новых источников"
                        errors = result.get("errors", [])
                        warning = f" Ошибки: {len(errors)}." if errors else ""
                        message = (
                            "Memory Center обновлен. "
                            f"Источники: {successful}. "
                            f"Добавлено/обновлено элементов: {ingested}.{warning}"
                        )
                    else:
                        errors = result.get("errors") or []
                        if errors:
                            details = "; ".join(
                                str(item.get("error") or item.get("source") or "unknown")
                                for item in errors[:3]
                                if isinstance(item, dict)
                            )
                        else:
                            details = str(result.get("error", "unknown error"))
                        message = f"Не удалось обновить Memory Center: {details}"
                except Exception as exc:
                    ok = False
                    message = f"Не удалось обновить Memory Center: {exc}"

                def finish() -> None:
                    assistant_state.set(
                        AssistantStateName.IDLE if ok else AssistantStateName.ERROR,
                        message,
                    )
                    QMessageBox.information(self, "Memory Center", message)

                QTimer.singleShot(0, finish)

            threading.Thread(target=worker, daemon=True).start()

        def _run_quick_mic_test(self) -> None:
            if self._interaction_lock.locked():
                QMessageBox.information(
                    self,
                    "Тест микрофона",
                    "Сначала дождись завершения текущего голосового запроса.",
                )
                return

            assistant_state.set(AssistantStateName.THINKING, "Проверяю микрофон...")

            def worker() -> None:
                ok, message = _run_mic_health_check(2.0)

                def finish() -> None:
                    assistant_state.set(
                        AssistantStateName.IDLE if ok else AssistantStateName.ERROR,
                        message,
                    )
                    QMessageBox.information(self, "Тест микрофона", message)

                QTimer.singleShot(0, finish)

            threading.Thread(target=worker, daemon=True).start()

        def _open_text_command_dialog(self) -> None:
            dialog = TextCommandDialog(self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            command_text = dialog.command_text
            if not command_text:
                return
            self._start_text_command_thread(command_text)

        def _request_open_text_command_dialog(self) -> None:
            self._bridge.text_command_requested.emit()

        def _start_text_command_thread(self, command_text: str) -> None:
            if self._interaction_lock.locked():
                with self._text_command_control_lock:
                    cancel_event = self._text_command_cancel_event
                    if cancel_event is not None:
                        self._queued_text_command = command_text
                        cancel_event.set()
                        stop_speaking()
                        assistant_state.set(
                            AssistantStateName.THINKING,
                            "Останавливаю текущий ответ и переключаюсь на новую команду...",
                        )
                        return
                assistant_state.set(
                    AssistantStateName.THINKING,
                    "Секунду, сначала закончу текущий запрос.",
                )
                return

            def worker() -> None:
                cancel_event = threading.Event()
                with self._text_command_control_lock:
                    self._text_command_cancel_event = cancel_event
                with self._interaction_lock:
                    try:
                        assistant_state.set(
                            AssistantStateName.THINKING,
                            f"Разбираю текстовую команду: {command_text}",
                        )
                        streamed_response = ""
                        for event in run_text_pipeline(
                            command_text,
                            speak_response=True,
                            tts_backend_name="default",
                            speak_strategy="chunked",
                            should_stop=cancel_event.is_set,
                        ):
                            if event.stage == "intent_resolved":
                                assistant_state.set(
                                    AssistantStateName.THINKING,
                                    "Поняла задачу, формирую ответ...",
                                )
                                continue
                            if event.stage == "pipeline_canceled":
                                break
                            if event.stage != "response_stream":
                                continue
                            chunk = str(event.data.get("text", "")).strip()
                            if not chunk:
                                continue
                            streamed_response = f"{streamed_response} {chunk}".strip()
                            assistant_state.set(AssistantStateName.SPEAKING, streamed_response)
                    except Exception as exc:
                        message = f"Не удалось обработать текстовую команду: {exc}"
                        assistant_state.set(AssistantStateName.ERROR, message)
                        speak("Не удалось обработать текстовую команду.")
                with self._text_command_control_lock:
                    self._text_command_cancel_event = None
                    queued_command = self._queued_text_command
                    self._queued_text_command = None
                assistant_state.set(AssistantStateName.IDLE)
                action = assistant_control.consume_action()
                if action == AssistantControlAction.EXIT:
                    self._bridge.exit_requested.emit()
                elif action == AssistantControlAction.OPEN_TEXT_COMMAND:
                    self._bridge.text_command_requested.emit()
                if queued_command:
                    QTimer.singleShot(0, lambda: self._start_text_command_thread(queued_command))

            threading.Thread(target=worker, daemon=True).start()

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
                text_hotkey_hint = self._text_hotkey or HOTKEY_TEXT_COMBINATION
                message = (
                    "Привет. Я Вася и я рядом.\n"
                    f"Горячая клавиша: {hotkey_hint}\n"
                    f"Текстовая клавиша: {text_hotkey_hint}\n"
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
                    QTimer.singleShot(800, self._open_onboarding_dialog)

            QTimer.singleShot(300, show_onboarding)

        def _open_onboarding_dialog(self) -> None:
            dialog = OnboardingDialog(self)
            dialog.exec()

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

        def _apply_text_hotkey(self, hotkey_text: str) -> None:
            new_hotkey = normalize_hotkey_combination(hotkey_text)
            old_hotkey = self._text_hotkey
            self._text_hotkey = new_hotkey

            if self._hotkey_listener is not None:
                self._hotkey_listener.stop()
                self._hotkey_listener = None

            self._start_hotkey_listener()
            if self._hotkey_listener is None:
                self._text_hotkey = old_hotkey
                self._start_hotkey_listener()
                raise RuntimeError("Не удалось применить текстовую горячую клавишу.")

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
