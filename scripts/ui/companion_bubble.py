"""Compact desktop chat bubble using the public Vasya landing palette."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ResponseBubble(QWidget):
    question_submitted = Signal(str)
    voice_requested = Signal()
    dismissed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(340, 194)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 15)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("ВАСЯ", self)
        title.setStyleSheet("color: #fff1de; font-size: 11px; font-weight: 700; letter-spacing: 2px;")
        header.addWidget(title)
        header.addStretch(1)
        close_button = QPushButton("×", self)
        close_button.setAccessibleName("Закрыть окно вопроса")
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self._dismiss)
        close_button.setStyleSheet(
            "QPushButton { color: #b3b3b3; background: transparent; border: 0;"
            " font-size: 22px; } QPushButton:hover { color: #ffffff; }"
        )
        header.addWidget(close_button)
        layout.addLayout(header)

        self._answer = QTextEdit(self)
        self._answer.setReadOnly(True)
        self._answer.setAccessibleName("Ответ Васи")
        self._answer.setPlainText("Напишите вопрос или начните говорить.")
        self._answer.setStyleSheet(
            "QTextEdit { color: #fff1de; background: transparent; border: 0;"
            " font-size: 13px; selection-background-color: #b46a56; }"
        )
        layout.addWidget(self._answer, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(7)
        self._input = QLineEdit(self)
        self._input.setAccessibleName("Вопрос Васе")
        self._input.setPlaceholderText("Спросите Васю…")
        self._input.setMaxLength(4000)
        self._input.returnPressed.connect(self._submit)
        self._input.setStyleSheet(
            "QLineEdit { color: #fff1de; background: #281b3c; border: 1px solid #8d628f;"
            " border-radius: 8px; padding: 7px 9px; font-size: 12px; }"
            " QLineEdit:focus { border-color: #ffab52; }"
        )
        input_row.addWidget(self._input, 1)

        voice_button = QPushButton("🎙", self)
        voice_button.setAccessibleName("Начать говорить")
        voice_button.setFixedSize(34, 34)
        voice_button.clicked.connect(self.voice_requested)
        voice_button.setStyleSheet(
            "QPushButton { color: #fff1de; background: #39264f; border: 1px solid #8d628f;"
            " border-radius: 8px; } QPushButton:hover { border-color: #ffab52; }"
        )
        input_row.addWidget(voice_button)

        send_button = QPushButton("↑", self)
        send_button.setAccessibleName("Отправить вопрос")
        send_button.setFixedSize(34, 34)
        send_button.clicked.connect(self._submit)
        send_button.setStyleSheet(
            "QPushButton { color: #27162f; background: #ffab52; border: 0;"
            " border-radius: 8px; font-size: 18px; font-weight: 700; }"
            " QPushButton:hover { background: #ffc171; }"
        )
        input_row.addWidget(send_button)
        layout.addLayout(input_row)

    def set_text(self, text: str) -> None:
        self._answer.setPlainText(text or "Напишите вопрос или начните говорить.")
        scrollbar = self._answer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def focus_input(self) -> None:
        self.activateWindow()
        self._input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _submit(self) -> None:
        text = self._input.text().strip()
        if not text:
            self._input.setFocus()
            return
        self._input.clear()
        self.question_submitted.emit(text)

    def _dismiss(self) -> None:
        self.hide()
        self.dismissed.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._dismiss()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        _ = event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = self.rect().adjusted(1, 1, -1, -1)
        fill = QLinearGradient(card.topLeft(), card.bottomRight())
        fill.setColorAt(0, QColor(21, 16, 40, 248))
        fill.setColorAt(1, QColor(55, 31, 70, 248))
        painter.setBrush(fill)
        painter.setPen(QPen(QColor(182, 114, 195, 160), 1))
        painter.drawRoundedRect(card, 16, 16)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffab52"))
        painter.drawRoundedRect(16, 13, 28, 3, 1, 1)
