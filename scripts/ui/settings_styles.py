from __future__ import annotations


SETTINGS_DIALOG_STYLESHEET = """
QDialog {
    background-color: #0b0b0b;
    border: 1px solid #363636;
    border-radius: 8px;
}
QLabel {
    color: #f1f1f1;
    font-size: 13px;
}
QCheckBox {
    color: #f1f1f1;
    spacing: 8px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #505050;
    background: #151515;
}
QCheckBox::indicator:checked {
    background: #f1f1f1;
    border: 1px solid #f1f1f1;
}
QComboBox, QLineEdit {
    min-height: 20px;
    border: 1px solid #505050;
    border-radius: 8px;
    background: #151515;
    color: #f1f1f1;
    padding: 8px 10px;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    border: 1px solid #505050;
    border-radius: 8px;
    background: #1c1c1c;
    color: #f1f1f1;
    selection-background-color: #363636;
    selection-color: #ffffff;
    outline: 0;
}
QWidget#settingsTabPage,
QScrollArea,
QScrollArea > QWidget > QWidget {
    background: #151515;
}
QScrollArea {
    border: none;
}
QTabWidget#settingsTabs {
    background: transparent;
}
QTabWidget#settingsTabs::pane {
    margin-top: 6px;
    border: 1px solid #363636;
    border-radius: 8px;
    background: #151515;
}
QTabWidget#settingsTabs::tab-bar {
    alignment: left;
}
QTabWidget#settingsTabs > QWidget#qt_tabwidget_stackedwidget {
    border-radius: 8px;
    background: #151515;
}
QTabWidget#settingsTabs QTabBar {
    background: #0b0b0b;
}
QTabWidget#settingsTabs QTabBar::tab {
    margin-right: 4px;
    border: 1px solid #363636;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    background: #151515;
    color: #b3b3b3;
    padding: 8px 12px;
}
QTabWidget#settingsTabs QTabBar::tab:selected {
    border-color: #7a7a7a;
    background: #242424;
    color: #ffffff;
}
QTabWidget#settingsTabs QTabBar::tab:!selected {
    margin-top: 2px;
}
QSlider::groove:horizontal {
    height: 6px;
    border: 0;
    border-radius: 3px;
    background: #363636;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    border: 1px solid #ffffff;
    border-radius: 8px;
    background: #f1f1f1;
}
QPushButton {
    border: 1px solid #505050;
    border-radius: 8px;
    background: #242424;
    color: #f1f1f1;
    padding: 8px 14px;
}
QPushButton:hover {
    border-color: #7a7a7a;
    background: #303030;
}
QPushButton:default {
    border-color: #f1f1f1;
    background: #f1f1f1;
    color: #111111;
}
QDialogButtonBox QPushButton {
    min-width: 100px;
}
"""
