from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LineEditLike(Protocol):
    def setPlaceholderText(self, placeholder: str) -> None:
        ...

    def setEchoMode(self, echo_mode) -> None:
        ...


@dataclass(frozen=True)
class SettingsTextInput:
    field_name: str
    setting_key: str
    row_label: str
    placeholder: str
    is_secret: bool = False


INTEGRATION_TEXT_INPUTS: tuple[SettingsTextInput, ...] = (
    SettingsTextInput("github_repo", "github_default_repo", "GitHub repo", "owner/repo"),
    SettingsTextInput(
        "obsidian_vault",
        "obsidian_vault_path",
        "Obsidian vault path",
        "Path to local notes vault",
    ),
    SettingsTextInput(
        "notion_page",
        "notion_updates_page_id",
        "Notion page id",
        "Notion page id",
    ),
    SettingsTextInput(
        "github_token",
        "github_api_token",
        "GitHub token",
        "GitHub token (optional)",
        is_secret=True,
    ),
    SettingsTextInput(
        "notion_token",
        "notion_api_token",
        "Notion token",
        "Notion integration token",
        is_secret=True,
    ),
    SettingsTextInput(
        "dictation_api_url",
        "dictation_api_url",
        "Dictation API URL",
        "http://127.0.0.1:8787/v1/dictation",
    ),
    SettingsTextInput(
        "dictation_api_token",
        "dictation_api_token",
        "Dictation API token",
        "X-API-Key / Bearer token (optional)",
        is_secret=True,
    ),
)


def configure_text_input(
    line_edit: LineEditLike,
    spec: SettingsTextInput,
    *,
    password_echo_mode,
) -> None:
    if spec.is_secret:
        line_edit.setEchoMode(password_echo_mode)
    line_edit.setPlaceholderText(spec.placeholder)
