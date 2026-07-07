from __future__ import annotations

import unittest

from scripts.ui.settings_inputs import (
    INTEGRATION_TEXT_INPUTS,
    configure_text_input,
)


class _FakeLineEdit:
    def __init__(self) -> None:
        self.placeholder = None
        self.echo_mode = None

    def setPlaceholderText(self, placeholder: str) -> None:
        self.placeholder = placeholder

    def setEchoMode(self, echo_mode) -> None:
        self.echo_mode = echo_mode


class SettingsInputsTests(unittest.TestCase):
    def test_integration_text_inputs_keep_expected_order_and_values(self) -> None:
        self.assertEqual(
            [
                (spec.field_name, spec.setting_key, spec.row_label, spec.placeholder, spec.is_secret)
                for spec in INTEGRATION_TEXT_INPUTS
            ],
            [
                (
                    "github_repo",
                    "github_default_repo",
                    "GitHub repo",
                    "owner/repo",
                    False,
                ),
                (
                    "obsidian_vault",
                    "obsidian_vault_path",
                    "Obsidian vault path",
                    "Path to local notes vault",
                    False,
                ),
                (
                    "notion_page",
                    "notion_updates_page_id",
                    "Notion page id",
                    "Notion page id",
                    False,
                ),
                (
                    "github_token",
                    "github_api_token",
                    "GitHub token",
                    "GitHub token (optional)",
                    True,
                ),
                (
                    "notion_token",
                    "notion_api_token",
                    "Notion token",
                    "Notion integration token",
                    True,
                ),
                (
                    "dictation_api_url",
                    "dictation_api_url",
                    "Dictation API URL",
                    "http://127.0.0.1:8787/v1/dictation",
                    False,
                ),
                (
                    "dictation_api_token",
                    "dictation_api_token",
                    "Dictation API token",
                    "X-API-Key / Bearer token (optional)",
                    True,
                ),
            ],
        )

    def test_configure_text_input_applies_placeholder_and_secret_echo_mode(self) -> None:
        line_edit = _FakeLineEdit()

        configure_text_input(
            line_edit,
            INTEGRATION_TEXT_INPUTS[3],
            password_echo_mode="password",
        )

        self.assertEqual(line_edit.placeholder, "GitHub token (optional)")
        self.assertEqual(line_edit.echo_mode, "password")

    def test_configure_text_input_leaves_public_input_echo_mode_unchanged(self) -> None:
        line_edit = _FakeLineEdit()

        configure_text_input(
            line_edit,
            INTEGRATION_TEXT_INPUTS[0],
            password_echo_mode="password",
        )

        self.assertEqual(line_edit.placeholder, "owner/repo")
        self.assertIsNone(line_edit.echo_mode)


if __name__ == "__main__":
    unittest.main()
