from __future__ import annotations


SETTINGS_DIALOG_STYLESHEET = """
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
