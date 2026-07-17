from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from assistant.child_mode import child_mode_store
from config.settings import AVATAR_SKIN, MORNING_SHOW_CITY
from services.github_service import GitHubServiceError, fetch_recent_commits
from services.integration_settings_service import (
    get_integration_setting,
    save_integration_settings,
)
from services.morning_show_service import get_morning_show_message, reset_morning_show_today
from services.notion_service import NotionServiceError, read_page_text
from services.speed_report_service import build_voice_auto_tune_plan
from services.user_profile_service import clear_user_profile
from utils.logger import log
from utils.platform_runtime import get_platform_name
from voice.profiles import get_active_voice_profile, list_voice_profiles
from voice.tts import set_voice_profile, speak

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .avatar_geometry import snap_to_nearest_edge as _snap_to_nearest_screen_edge
from .avatar_skins import (
    available_pack_skin_ids as _available_pack_skin_ids,
    avatar_skin_ids as _avatar_skin_ids,
    avatar_skin_spec as _avatar_skin_spec,
    delete_custom_skin_spec as _delete_custom_skin_spec,
    exportable_skin_spec as _exportable_skin_spec,
    pack_manifest_path as _pack_manifest_path,
    pack_skin_combo_value as _pack_skin_combo_value,
    pack_skin_from_combo_value as _pack_skin_from_combo_value,
    save_custom_skin_spec as _save_custom_skin_spec,
)
from .settings_dialog_specs import (
    SETTINGS_DIALOG_BUTTON_LABELS,
    SETTINGS_DIALOG_CHECKBOX_LABELS,
    SETTINGS_DIALOG_HEADER_TEXTS,
    SETTINGS_DIALOG_OBJECT_NAMES,
    SETTINGS_DIALOG_PLACEHOLDERS,
    SETTINGS_DIALOG_ROW_LABELS,
    SETTINGS_DIALOG_TOOLTIPS,
)
from .settings_inputs import INTEGRATION_TEXT_INPUTS, configure_text_input
from .settings_layout import (
    add_action_row_widgets,
    configure_checkbox_input,
    configure_decimal_value_input,
    configure_ranged_value_input,
    configure_settings_form_layout,
    configure_slider_value_input,
)
from .settings_options import (
    AGENT_ROUTING_PROFILE_OPTIONS,
    AVATAR_SIZE_OPTIONS,
    CHAT_PROMPT_PACK_OPTIONS,
    DICTATION_TARGET_OPTIONS,
    TRAY_CLICK_OPTIONS,
    populate_combo_options,
    populate_voice_profile_options,
)
from .settings_preview import AvatarPreview
from .settings_styles import SETTINGS_DIALOG_STYLESHEET
from .settings_tabs import SETTINGS_TABS

BRAND_ACCENT_ALT = "#7b3dff"
BRAND_MUTED = "#9fb8ec"


if get_platform_name() == "macos":
    try:
        from scripts.autostart_macos import install_autostart, uninstall_autostart
    except ImportError:
        from autostart_macos import install_autostart, uninstall_autostart
else:
    def install_autostart() -> None:
        raise RuntimeError("Autostart is currently available only on macOS.")

    def uninstall_autostart() -> None:
        return None


def _snap_to_nearest_edge(position, width: int, height: int):
    return _snap_to_nearest_screen_edge(
        position,
        width,
        height,
        screen_provider=QGuiApplication,
        point_factory=position.__class__,
    )


class SettingsDialog(QDialog):
    def __init__(self, widget: "AvatarWidget") -> None:
        super().__init__(widget)
        self.setWindowTitle(SETTINGS_DIALOG_HEADER_TEXTS.window_title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self._widget = widget
        self.setStyleSheet(SETTINGS_DIALOG_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(14)

        title = QLabel(SETTINGS_DIALOG_HEADER_TEXTS.title, self)
        title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {BRAND_ACCENT_ALT};")
        subtitle = QLabel(SETTINGS_DIALOG_HEADER_TEXTS.subtitle, self)
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
        self._preview = AvatarPreview(widget, self)
        preview_layout.addWidget(self._preview, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(preview_wrap)

        tabs = QTabWidget(self)
        tabs.setObjectName(SETTINGS_DIALOG_OBJECT_NAMES.tabs)
        tabs.setDocumentMode(True)
        tabs.tabBar().setDrawBase(False)

        tab_pages = {}
        for tab_spec in SETTINGS_TABS:
            tab_page = QWidget(self)
            tab_page.setObjectName(SETTINGS_DIALOG_OBJECT_NAMES.tab_page)
            tabs.addTab(tab_page, tab_spec.label)
            tab_pages[tab_spec.tab_id] = tab_page
        appearance_tab = tab_pages["appearance"]
        behavior_tab = tab_pages["behavior"]
        integrations_tab = tab_pages["integrations"]

        appearance_form = QFormLayout(appearance_tab)
        behavior_form = QFormLayout(behavior_tab)
        integrations_form = QFormLayout(integrations_tab)
        for form_layout in (appearance_form, behavior_form, integrations_form):
            configure_settings_form_layout(
                form_layout,
                label_alignment=Qt.AlignmentFlag.AlignLeft,
                form_alignment=Qt.AlignmentFlag.AlignTop,
            )

        self._build_appearance_section(appearance_form, widget)
        self._build_behavior_section(behavior_form, widget)
        self._build_integrations_section(integrations_form)

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

    def _build_appearance_section(self, appearance_form: QFormLayout, widget: "AvatarWidget") -> None:
        self._size_combo = QComboBox(self)
        populate_combo_options(self._size_combo, AVATAR_SIZE_OPTIONS)
        self._select_combo_value(self._size_combo, widget._avatar_size)
        self._size_combo.currentIndexChanged.connect(self._sync_preview)
        appearance_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.avatar_size,
            self._size_combo,
        )

        self._skin_combo = QComboBox(self)
        self._skin_combo.currentIndexChanged.connect(self._sync_preview)
        self._reload_skin_choices(widget._avatar_skin)

        skin_actions = QHBoxLayout()
        import_skin_button = QPushButton(
            SETTINGS_DIALOG_BUTTON_LABELS.import_skin,
            self,
        )
        import_skin_button.clicked.connect(self._import_custom_skin)
        export_skin_button = QPushButton(
            SETTINGS_DIALOG_BUTTON_LABELS.export_skin,
            self,
        )
        export_skin_button.clicked.connect(self._export_current_skin)
        reset_skin_button = QPushButton(SETTINGS_DIALOG_BUTTON_LABELS.reset_skin, self)
        reset_skin_button.clicked.connect(self._reset_custom_skin)
        add_action_row_widgets(
            skin_actions,
            (import_skin_button, export_skin_button, reset_skin_button),
        )

        skin_row = QVBoxLayout()
        skin_row.setSpacing(8)
        skin_row.addWidget(self._skin_combo)
        skin_row.addLayout(skin_actions)
        appearance_form.addRow(SETTINGS_DIALOG_ROW_LABELS.avatar_skin, skin_row)

        image_actions = QHBoxLayout()
        choose_image_button = QPushButton(
            SETTINGS_DIALOG_BUTTON_LABELS.choose_avatar_image,
            self,
        )
        choose_image_button.clicked.connect(self._choose_avatar_image)
        reset_image_button = QPushButton(
            SETTINGS_DIALOG_BUTTON_LABELS.reset_avatar_image,
            self,
        )
        reset_image_button.clicked.connect(self._reset_avatar_image)
        add_action_row_widgets(image_actions, (choose_image_button, reset_image_button))
        appearance_form.addRow(SETTINGS_DIALOG_ROW_LABELS.avatar_image, image_actions)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal, self)
        configure_slider_value_input(
            self._opacity_slider,
            minimum=70,
            maximum=100,
            step=5,
            value=int(widget._avatar_opacity * 100),
        )
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self._opacity_slider)
        self._opacity_label = QLabel(f"{int(widget._avatar_opacity * 100)}%")
        opacity_row.addWidget(self._opacity_label)
        self._opacity_slider.valueChanged.connect(
            lambda value: self._opacity_label.setText(f"{value}%")
        )
        self._opacity_slider.valueChanged.connect(self._sync_preview)
        appearance_form.addRow(SETTINGS_DIALOG_ROW_LABELS.avatar_opacity, opacity_row)

        self._idle_motion_checkbox = QCheckBox(
            SETTINGS_DIALOG_CHECKBOX_LABELS.idle_motion,
            self,
        )
        configure_checkbox_input(
            self._idle_motion_checkbox,
            checked=widget._idle_motion_enabled,
        )
        self._idle_motion_checkbox.toggled.connect(self._sync_preview)
        appearance_form.addRow(self._idle_motion_checkbox)

    def _build_behavior_section(self, behavior_form: QFormLayout, widget: "AvatarWidget") -> None:
        self._voice_profile_combo = QComboBox(self)
        active_profile = get_active_voice_profile()
        populate_voice_profile_options(self._voice_profile_combo, list_voice_profiles())
        self._select_combo_value(self._voice_profile_combo, active_profile.profile_id)
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.voice_profile,
            self._voice_profile_combo,
        )

        self._tray_click_combo = QComboBox(self)
        populate_combo_options(self._tray_click_combo, TRAY_CLICK_OPTIONS)
        self._select_combo_value(self._tray_click_combo, widget._tray_click_action)
        behavior_form.addRow(SETTINGS_DIALOG_ROW_LABELS.tray_click, self._tray_click_combo)

        self._show_bubble_checkbox = QCheckBox(
            SETTINGS_DIALOG_CHECKBOX_LABELS.show_bubble,
            self,
        )
        configure_checkbox_input(
            self._show_bubble_checkbox,
            checked=widget._show_response_bubble,
        )
        behavior_form.addRow(self._show_bubble_checkbox)

        self._child_mode_checkbox = QCheckBox(SETTINGS_DIALOG_CHECKBOX_LABELS.child_mode, self)
        configure_checkbox_input(
            self._child_mode_checkbox,
            checked=child_mode_store.is_enabled(),
        )
        behavior_form.addRow(self._child_mode_checkbox)

        self._morning_show_checkbox = QCheckBox(
            SETTINGS_DIALOG_CHECKBOX_LABELS.morning_show,
            self,
        )
        configure_checkbox_input(
            self._morning_show_checkbox,
            checked=widget._morning_show_enabled,
        )
        behavior_form.addRow(self._morning_show_checkbox)

        self._morning_show_city_input = QLineEdit(widget._morning_show_city, self)
        self._morning_show_city_input.setPlaceholderText(
            SETTINGS_DIALOG_PLACEHOLDERS.morning_show_city
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.morning_show_city,
            self._morning_show_city_input,
        )

        self._morning_show_hour_limit = QSpinBox(self)
        configure_ranged_value_input(
            self._morning_show_hour_limit,
            minimum=0,
            maximum=23,
            value=widget._morning_show_hour_limit,
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.morning_show_hour_limit,
            self._morning_show_hour_limit,
        )

        self._smart_followup_checkbox = QCheckBox(
            SETTINGS_DIALOG_CHECKBOX_LABELS.smart_followup,
            self,
        )
        configure_checkbox_input(
            self._smart_followup_checkbox,
            checked=widget._smart_followup_enabled,
        )
        behavior_form.addRow(self._smart_followup_checkbox)

        self._smart_followup_seconds = QDoubleSpinBox(self)
        configure_decimal_value_input(
            self._smart_followup_seconds,
            minimum=1.0,
            maximum=8.0,
            step=0.5,
            value=widget._smart_followup_listen_seconds,
            suffix=" с",
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.smart_followup_seconds,
            self._smart_followup_seconds,
        )

        self._smart_followup_retries = QSpinBox(self)
        configure_ranged_value_input(
            self._smart_followup_retries,
            minimum=1,
            maximum=3,
            value=widget._smart_followup_retries,
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.smart_followup_retries,
            self._smart_followup_retries,
        )

        self._auto_interrupt_checkbox = QCheckBox(
            SETTINGS_DIALOG_CHECKBOX_LABELS.auto_interrupt,
            self,
        )
        configure_checkbox_input(
            self._auto_interrupt_checkbox,
            checked=widget._auto_interrupt_tts_enabled,
        )
        behavior_form.addRow(self._auto_interrupt_checkbox)

        self._auto_interrupt_sample_seconds = QDoubleSpinBox(self)
        configure_decimal_value_input(
            self._auto_interrupt_sample_seconds,
            minimum=0.5,
            maximum=3.0,
            step=0.1,
            value=widget._auto_interrupt_sample_seconds,
            suffix=" с",
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.auto_interrupt_sample_seconds,
            self._auto_interrupt_sample_seconds,
        )

        self._auto_interrupt_adaptive_checkbox = QCheckBox(
            SETTINGS_DIALOG_CHECKBOX_LABELS.auto_interrupt_adaptive,
            self,
        )
        configure_checkbox_input(
            self._auto_interrupt_adaptive_checkbox,
            checked=widget._auto_interrupt_adaptive_enabled,
            tooltip=SETTINGS_DIALOG_TOOLTIPS.auto_interrupt_adaptive,
        )
        behavior_form.addRow(self._auto_interrupt_adaptive_checkbox)

        self._auto_interrupt_quiet_rms = QDoubleSpinBox(self)
        configure_decimal_value_input(
            self._auto_interrupt_quiet_rms,
            minimum=50.0,
            maximum=600.0,
            step=5.0,
            value=widget._auto_interrupt_quiet_rms_threshold,
            suffix=" RMS",
        )
        self._auto_interrupt_quiet_rms.setToolTip(
            SETTINGS_DIALOG_TOOLTIPS.auto_interrupt_quiet_rms
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.auto_interrupt_quiet_rms,
            self._auto_interrupt_quiet_rms,
        )

        self._auto_interrupt_noisy_rms = QDoubleSpinBox(self)
        configure_decimal_value_input(
            self._auto_interrupt_noisy_rms,
            minimum=80.0,
            maximum=900.0,
            step=5.0,
            value=widget._auto_interrupt_noisy_rms_threshold,
            suffix=" RMS",
        )
        self._auto_interrupt_noisy_rms.setToolTip(
            SETTINGS_DIALOG_TOOLTIPS.auto_interrupt_noisy_rms
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.auto_interrupt_noisy_rms,
            self._auto_interrupt_noisy_rms,
        )

        self._auto_interrupt_hits_quiet = QSpinBox(self)
        configure_ranged_value_input(
            self._auto_interrupt_hits_quiet,
            minimum=1,
            maximum=6,
            value=widget._auto_interrupt_hits_quiet,
        )
        self._auto_interrupt_hits_quiet.setToolTip(
            SETTINGS_DIALOG_TOOLTIPS.auto_interrupt_hits_quiet
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.auto_interrupt_hits_quiet,
            self._auto_interrupt_hits_quiet,
        )

        self._auto_interrupt_hits_normal = QSpinBox(self)
        configure_ranged_value_input(
            self._auto_interrupt_hits_normal,
            minimum=1,
            maximum=6,
            value=widget._auto_interrupt_hits_normal,
        )
        self._auto_interrupt_hits_normal.setToolTip(
            SETTINGS_DIALOG_TOOLTIPS.auto_interrupt_hits_normal
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.auto_interrupt_hits_normal,
            self._auto_interrupt_hits_normal,
        )

        self._auto_interrupt_hits_noisy = QSpinBox(self)
        configure_ranged_value_input(
            self._auto_interrupt_hits_noisy,
            minimum=1,
            maximum=6,
            value=widget._auto_interrupt_hits_noisy,
        )
        self._auto_interrupt_hits_noisy.setToolTip(
            SETTINGS_DIALOG_TOOLTIPS.auto_interrupt_hits_noisy
        )
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.auto_interrupt_hits_noisy,
            self._auto_interrupt_hits_noisy,
        )
        self._auto_interrupt_adaptive_checkbox.toggled.connect(self._sync_auto_interrupt_controls)
        self._auto_interrupt_quiet_rms.valueChanged.connect(self._sync_auto_interrupt_thresholds)
        self._sync_auto_interrupt_controls()

        self._routing_profile_combo = QComboBox(self)
        populate_combo_options(self._routing_profile_combo, AGENT_ROUTING_PROFILE_OPTIONS)
        self._select_combo_value(self._routing_profile_combo, widget._agent_routing_profile)
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.routing_profile,
            self._routing_profile_combo,
        )

        self._prompt_pack_profile_combo = QComboBox(self)
        populate_combo_options(self._prompt_pack_profile_combo, CHAT_PROMPT_PACK_OPTIONS)
        self._select_combo_value(self._prompt_pack_profile_combo, widget._chat_prompt_pack_profile)
        behavior_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.prompt_pack_profile,
            self._prompt_pack_profile_combo,
        )

        tuning_actions = QHBoxLayout()
        auto_tune_button = QPushButton(SETTINGS_DIALOG_BUTTON_LABELS.auto_tune, self)
        auto_tune_button.clicked.connect(self._run_voice_auto_tune)
        add_action_row_widgets(tuning_actions, (auto_tune_button,))
        behavior_form.addRow(SETTINGS_DIALOG_ROW_LABELS.auto_tune, tuning_actions)

        morning_actions = QHBoxLayout()
        test_morning_show_button = QPushButton(
            SETTINGS_DIALOG_BUTTON_LABELS.test_morning_show,
            self,
        )
        test_morning_show_button.clicked.connect(self._test_morning_show)
        reset_morning_show_button = QPushButton(
            SETTINGS_DIALOG_BUTTON_LABELS.reset_morning_show,
            self,
        )
        reset_morning_show_button.clicked.connect(self._reset_morning_show_today)
        add_action_row_widgets(
            morning_actions,
            (test_morning_show_button, reset_morning_show_button),
        )
        behavior_form.addRow(SETTINGS_DIALOG_ROW_LABELS.morning_show_check, morning_actions)

        self._snap_checkbox = QCheckBox(SETTINGS_DIALOG_CHECKBOX_LABELS.snap_to_edge, self)
        configure_checkbox_input(
            self._snap_checkbox,
            checked=widget._snap_to_edge_enabled,
        )
        behavior_form.addRow(self._snap_checkbox)

        self._start_hidden_checkbox = QCheckBox(
            SETTINGS_DIALOG_CHECKBOX_LABELS.start_hidden,
            self,
        )
        configure_checkbox_input(
            self._start_hidden_checkbox,
            checked=widget._start_hidden,
        )
        behavior_form.addRow(self._start_hidden_checkbox)

        if get_platform_name() == "macos":
            self._autostart_checkbox = QCheckBox(
                SETTINGS_DIALOG_CHECKBOX_LABELS.launch_at_login,
                self,
            )
            configure_checkbox_input(
                self._autostart_checkbox,
                checked=widget._launch_at_login_enabled,
            )
            behavior_form.addRow(self._autostart_checkbox)
        else:
            self._autostart_checkbox = None

        self._hotkey_input = QLineEdit(widget._activation_hotkey, self)
        behavior_form.addRow(SETTINGS_DIALOG_ROW_LABELS.hotkey, self._hotkey_input)
        self._text_hotkey_input = QLineEdit(widget._text_hotkey, self)
        behavior_form.addRow(SETTINGS_DIALOG_ROW_LABELS.text_hotkey, self._text_hotkey_input)

    def _build_integrations_section(
        self,
        integrations_form: QFormLayout,
    ) -> None:
        (
            github_repo_spec,
            obsidian_vault_spec,
            notion_page_spec,
            github_token_spec,
            notion_token_spec,
            dictation_api_url_spec,
            dictation_api_token_spec,
        ) = INTEGRATION_TEXT_INPUTS

        self._github_repo_input = QLineEdit(
            get_integration_setting(github_repo_spec.setting_key),
            self,
        )
        configure_text_input(
            self._github_repo_input,
            github_repo_spec,
            password_echo_mode=QLineEdit.EchoMode.Password,
        )
        integrations_form.addRow(github_repo_spec.row_label, self._github_repo_input)

        self._obsidian_vault_input = QLineEdit(
            get_integration_setting(obsidian_vault_spec.setting_key),
            self,
        )
        configure_text_input(
            self._obsidian_vault_input,
            obsidian_vault_spec,
            password_echo_mode=QLineEdit.EchoMode.Password,
        )
        integrations_form.addRow(obsidian_vault_spec.row_label, self._obsidian_vault_input)

        self._notion_page_input = QLineEdit(
            get_integration_setting(notion_page_spec.setting_key),
            self,
        )
        configure_text_input(
            self._notion_page_input,
            notion_page_spec,
            password_echo_mode=QLineEdit.EchoMode.Password,
        )
        integrations_form.addRow(notion_page_spec.row_label, self._notion_page_input)

        self._github_token_input = QLineEdit(
            get_integration_setting(github_token_spec.setting_key),
            self,
        )
        configure_text_input(
            self._github_token_input,
            github_token_spec,
            password_echo_mode=QLineEdit.EchoMode.Password,
        )
        integrations_form.addRow(github_token_spec.row_label, self._github_token_input)

        self._notion_token_input = QLineEdit(
            get_integration_setting(notion_token_spec.setting_key),
            self,
        )
        configure_text_input(
            self._notion_token_input,
            notion_token_spec,
            password_echo_mode=QLineEdit.EchoMode.Password,
        )
        integrations_form.addRow(notion_token_spec.row_label, self._notion_token_input)

        self._dictation_target_combo = QComboBox(self)
        populate_combo_options(self._dictation_target_combo, DICTATION_TARGET_OPTIONS)
        self._select_combo_value(self._dictation_target_combo, widget._dictation_target)
        integrations_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.dictation_target,
            self._dictation_target_combo,
        )

        self._dictation_api_url_input = QLineEdit(
            get_integration_setting(dictation_api_url_spec.setting_key),
            self,
        )
        configure_text_input(
            self._dictation_api_url_input,
            dictation_api_url_spec,
            password_echo_mode=QLineEdit.EchoMode.Password,
        )
        integrations_form.addRow(dictation_api_url_spec.row_label, self._dictation_api_url_input)

        self._dictation_api_token_input = QLineEdit(
            get_integration_setting(dictation_api_token_spec.setting_key),
            self,
        )
        configure_text_input(
            self._dictation_api_token_input,
            dictation_api_token_spec,
            password_echo_mode=QLineEdit.EchoMode.Password,
        )
        integrations_form.addRow(dictation_api_token_spec.row_label, self._dictation_api_token_input)

        integration_actions = QHBoxLayout()
        test_integrations_button = QPushButton(
            SETTINGS_DIALOG_BUTTON_LABELS.test_integrations,
            self,
        )
        test_integrations_button.clicked.connect(self._test_integrations)
        add_action_row_widgets(integration_actions, (test_integrations_button,))
        integrations_form.addRow(
            SETTINGS_DIALOG_ROW_LABELS.integrations_check,
            integration_actions,
        )

        memory_actions = QHBoxLayout()
        clear_memory_button = QPushButton(SETTINGS_DIALOG_BUTTON_LABELS.clear_memory, self)
        clear_memory_button.clicked.connect(self._clear_personal_memory)
        add_action_row_widgets(memory_actions, (clear_memory_button,))
        integrations_form.addRow(SETTINGS_DIALOG_ROW_LABELS.personal_memory, memory_actions)

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
