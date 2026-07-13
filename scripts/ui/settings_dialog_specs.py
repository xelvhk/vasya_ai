from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SettingsDialogObjectNames:
    tabs: str = "settingsTabs"
    tab_page: str = "settingsTabPage"


@dataclass(frozen=True)
class SettingsDialogHeaderTexts:
    window_title: str = "Настройки Васи"
    title: str = "Настройки Васи"
    subtitle: str = (
        "Управление поведением виджета, автозапуском "
        "и голосовой активацией."
    )


@dataclass(frozen=True)
class SettingsDialogRowLabels:
    avatar_size: str = "Размер Васи"
    avatar_skin: str = "Скин Васи"
    avatar_image: str = "Картинка Васи"
    avatar_opacity: str = "Прозрачность Васи"
    voice_profile: str = "Голос Васи"
    tray_click: str = "Клик по иконке в трее"
    morning_show_city: str = "Город утреннего шоу"
    morning_show_hour_limit: str = "До какого часа"
    smart_followup_seconds: str = "Окно дослушивания"
    smart_followup_retries: str = "Повторы в follow-up"
    auto_interrupt_sample_seconds: str = "Окно barge-in"
    auto_interrupt_quiet_rms: str = "Порог тихой среды"
    auto_interrupt_noisy_rms: str = "Порог шумной среды"
    auto_interrupt_hits_quiet: str = "Подтверждений (тихо)"
    auto_interrupt_hits_normal: str = "Подтверждений (обычно)"
    auto_interrupt_hits_noisy: str = "Подтверждений (шумно)"
    routing_profile: str = "A/B: Routing профиль"
    prompt_pack_profile: str = "A/B: Prompt pack профиль"
    auto_tune: str = "Auto-tune"
    morning_show_check: str = "Проверка"
    dictation_target: str = "Режим диктовки"
    integrations_check: str = "Notion/GitHub"
    personal_memory: str = "Память о пользователе"
    hotkey: str = "Горячая клавиша"
    text_hotkey: str = "Текстовая клавиша"


@dataclass(frozen=True)
class SettingsDialogButtonLabels:
    import_skin: str = "Импорт палитры..."
    export_skin: str = "Экспорт палитры..."
    reset_skin: str = "Сбросить свою"
    choose_avatar_image: str = "Выбрать изображение..."
    reset_avatar_image: str = "Вернуть встроенный"
    auto_tune: str = "Подобрать автоматически"
    test_morning_show: str = "Тест утреннего шоу"
    reset_morning_show: str = "Сбросить на сегодня"
    test_integrations: str = "Проверить интеграции"
    clear_memory: str = "Очистить личную память..."


@dataclass(frozen=True)
class SettingsDialogCheckboxLabels:
    show_bubble: str = "Показывать пузырь ответа"
    child_mode: str = "Детский режим"
    morning_show: str = "Утреннее шоу (первое обращение за день)"
    smart_followup: str = "Умный follow-up после ответа"
    auto_interrupt: str = (
        "Прерывать озвучивание новой голосовой командой"
    )
    auto_interrupt_adaptive: str = "Адаптивный auto-interrupt (тихо/шумно)"
    idle_motion: str = "Плавное движение в покое"
    snap_to_edge: str = "Прилипать к краю экрана"
    start_hidden: str = "Запускать скрытым"
    launch_at_login: str = "Запускать при входе"


@dataclass(frozen=True)
class SettingsDialogPlaceholders:
    morning_show_city: str = "Город для погоды, например Moscow"


@dataclass(frozen=True)
class SettingsDialogTooltips:
    auto_interrupt_adaptive: str = (
        "Рекомендуется: включено. "
        "В тихой среде прерывает быстрее, "
        "в шумной осторожнее."
    )
    auto_interrupt_quiet_rms: str = "Рекомендуется: 140 RMS"
    auto_interrupt_noisy_rms: str = "Рекомендуется: 260 RMS"
    auto_interrupt_hits_quiet: str = "Рекомендуется: 1 подтверждение"
    auto_interrupt_hits_normal: str = "Рекомендуется: 2 подтверждения"
    auto_interrupt_hits_noisy: str = "Рекомендуется: 3 подтверждения"


SETTINGS_DIALOG_OBJECT_NAMES = SettingsDialogObjectNames()
SETTINGS_DIALOG_HEADER_TEXTS = SettingsDialogHeaderTexts()
SETTINGS_DIALOG_ROW_LABELS = SettingsDialogRowLabels()
SETTINGS_DIALOG_BUTTON_LABELS = SettingsDialogButtonLabels()
SETTINGS_DIALOG_CHECKBOX_LABELS = SettingsDialogCheckboxLabels()
SETTINGS_DIALOG_PLACEHOLDERS = SettingsDialogPlaceholders()
SETTINGS_DIALOG_TOOLTIPS = SettingsDialogTooltips()
