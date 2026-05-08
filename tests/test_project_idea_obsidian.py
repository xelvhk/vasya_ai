from __future__ import annotations

import unittest
from unittest.mock import patch

from services.github_obsidian_sync_service import (
    _detect_project_type,
    _derive_note_title,
    _normalize_project_plan_markdown,
    analyze_project_idea_to_obsidian,
)
from utils.intent_fastpaths import detect_fast_intent


class ProjectIdeaObsidianTests(unittest.TestCase):
    def test_analyze_project_idea_to_obsidian_requires_longer_idea(self) -> None:
        result = analyze_project_idea_to_obsidian(idea="сделать приложение", title="test")
        self.assertIn("слишком короткая", result.lower())

    def test_analyze_project_idea_to_obsidian_writes_markdown_note(self) -> None:
        idea = "сервис для контроля личных финансов с бюджетами, целями и еженедельными отчетами"
        with patch("services.github_obsidian_sync_service.resolve_chat_model", return_value="fake-model"):
            with patch("services.github_obsidian_sync_service.generate", return_value="- [ ] (P0) Сделать MVP"):
                with patch(
                    "services.github_obsidian_sync_service.upsert_obsidian_note",
                    return_value={"ok": True, "path": "/tmp/Idea.md"},
                ) as upsert_mock:
                    result = analyze_project_idea_to_obsidian(idea=idea, title="Finance MVP")

        self.assertIn("записала план", result.lower())
        kwargs = upsert_mock.call_args.kwargs
        self.assertEqual(kwargs["title"], "Finance MVP")
        self.assertEqual(kwargs["mode"], "replace")
        self.assertIn("Исходная идея", kwargs["content"])
        self.assertIn("План реализации", kwargs["content"])

    def test_analyze_project_idea_to_obsidian_normalizes_unstructured_plan(self) -> None:
        idea = "инструмент для контроля питания с дневником и напоминаниями"
        raw_plan = (
            "Сначала уточнить аудиторию. "
            "Потом сделать прототип. "
            "Проверить на первых пользователях."
        )
        with patch("services.github_obsidian_sync_service.resolve_chat_model", return_value="fake-model"):
            with patch("services.github_obsidian_sync_service.generate", return_value=raw_plan):
                with patch(
                    "services.github_obsidian_sync_service.upsert_obsidian_note",
                    return_value={"ok": True, "path": "/tmp/Idea2.md"},
                ) as upsert_mock:
                    result = analyze_project_idea_to_obsidian(idea=idea, title="Nutrition Plan")

        self.assertIn("записала план", result.lower())
        content = upsert_mock.call_args.kwargs["content"]
        self.assertIn("### Цель и ценность", content)
        self.assertIn("### MVP", content)
        self.assertIn("### Этапы реализации", content)
        self.assertIn("### Задачи по этапам", content)
        self.assertIn("### Архитектурные решения", content)
        self.assertIn("### Риски и как снизить", content)
        self.assertIn("### Что сделать сегодня", content)
        self.assertIn("- [ ]", content)

    def test_analyze_project_idea_to_obsidian_includes_project_type_in_prompt(self) -> None:
        idea = "telegram бот для записи клиентов салона и напоминаний о визитах"
        with patch("services.github_obsidian_sync_service.resolve_chat_model", return_value="fake-model"):
            with patch(
                "services.github_obsidian_sync_service.generate",
                return_value="- [ ] Сделать команды /start и /help",
            ) as generate_mock:
                with patch(
                    "services.github_obsidian_sync_service.upsert_obsidian_note",
                    return_value={"ok": True, "path": "/tmp/Idea3.md"},
                ) as upsert_mock:
                    result = analyze_project_idea_to_obsidian(idea=idea, title="Salon Bot")

        self.assertIn("записала план", result.lower())
        prompt = generate_mock.call_args.args[0]
        self.assertIn("Тип проекта: Telegram-бот", prompt)
        content = upsert_mock.call_args.kwargs["content"]
        self.assertIn("## Тип проекта", content)
        self.assertIn("Telegram-бот", content)

    def test_detect_project_type_mobile(self) -> None:
        self.assertEqual(
            _detect_project_type("mobile приложение для учета финансов на ios и android"),
            "mobile_app",
        )

    def test_normalize_uses_voice_assistant_default_tasks(self) -> None:
        normalized = _normalize_project_plan_markdown(
            "Сначала описать продукт. Потом сделать MVP.",
            project_type="voice_assistant",
        )
        self.assertIn("STT -> intent -> TTS", normalized)
        self.assertIn("UX-метрики: TTFR, TTA", normalized)

    def test_auto_title_template_includes_project_type(self) -> None:
        title = _derive_note_title(
            "telegram бот для записи клиентов салона красоты",
            project_type="telegram_bot",
        )
        self.assertIn("Idea Plan • Telegram-бот:", title)
        self.assertIn("telegram бот", title.lower())

    def test_normalize_uses_type_specific_phases_with_release_and_security(self) -> None:
        normalized = _normalize_project_plan_markdown(
            "Набросок без структуры.",
            project_type="desktop_app",
        )
        self.assertIn("упаковка, обновления и релиз", normalized)
        self.assertIn("### Этапы реализации", normalized)
        self.assertIn("### Архитектурные решения", normalized)
        self.assertIn("allowlist + подтверждение рискованных команд", normalized)


class ProjectIdeaIntentFastpathTests(unittest.TestCase):
    def test_detect_fast_intent_for_project_idea_to_obsidian(self) -> None:
        text = (
            "Проанализируй идею проекта ассистент для родителей и распиши задачи по реализации в обсидиан"
        )
        intent = detect_fast_intent(text)
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "analyze_project_idea_to_obsidian")
        self.assertIn("ассистент для родителей", intent.data["idea"])

    def test_detect_fast_intent_with_explicit_obsidian_note_title(self) -> None:
        text = (
            "Составь план по идее помощник для изучения языков в заметку Language Coach MVP в обсидиан"
        )
        intent = detect_fast_intent(text)
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "analyze_project_idea_to_obsidian")
        self.assertIn("помощник для изучения языков", intent.data["idea"])
        self.assertEqual(intent.data.get("title"), "Language Coach MVP")

    def test_detect_fast_intent_with_quoted_title(self) -> None:
        text = (
            'Проанализируй идею "планировщик обучения" в заметку "My Learning Plan" в обсидиан'
        )
        intent = detect_fast_intent(text)
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.intent, "analyze_project_idea_to_obsidian")
        self.assertEqual(intent.data.get("idea"), "планировщик обучения")
        self.assertEqual(intent.data.get("title"), "My Learning Plan")


if __name__ == "__main__":
    unittest.main()
