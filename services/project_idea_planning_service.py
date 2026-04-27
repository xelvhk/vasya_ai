from __future__ import annotations

from assistant.project_idea_planning import project_idea_planning_store
from services.github_obsidian_sync_service import analyze_project_idea_to_obsidian

_STEP_FIELDS: tuple[tuple[str, str], ...] = (
    ("audience", "Для кого этот проект в первую очередь?"),
    ("platform", "Где он будет жить на старте: web, mobile, desktop, Telegram-бот или другое?"),
    ("goal", "Какой главный результат хочешь получить в первые 4-6 недель?"),
)

_CANCEL_PHRASES = {
    "отмена",
    "отмени",
    "стоп",
    "хватит",
    "не надо",
}

_SKIP_PHRASES = {
    "пропусти",
    "дальше",
    "не знаю",
}


def handle_project_idea_request(*, idea: str, title: str | None = None) -> str:
    normalized_idea = " ".join(str(idea or "").strip().split())
    normalized_title = " ".join(str(title or "").strip().split()) or None
    if _is_idea_incomplete(normalized_idea):
        project_idea_planning_store.start(
            base_idea=normalized_idea,
            note_title=normalized_title,
        )
        return (
            "Чтобы сделать хороший план, уточню пару вещей. "
            f"{_STEP_FIELDS[0][1]}"
        )
    return analyze_project_idea_to_obsidian(
        idea=normalized_idea,
        title=normalized_title,
    )


def continue_project_idea_clarification(user_text: str) -> str | None:
    pending = project_idea_planning_store.get()
    if pending is None:
        return None

    normalized_reply = " ".join(str(user_text or "").strip().split())
    compact = normalized_reply.lower()
    if compact in _CANCEL_PHRASES:
        project_idea_planning_store.clear()
        return "Хорошо, отменяю подготовку проектного плана."

    step_index = pending.step_index
    answers = dict(pending.answers)
    if step_index < len(_STEP_FIELDS):
        field_name = _STEP_FIELDS[step_index][0]
        if compact not in _SKIP_PHRASES and normalized_reply:
            answers[field_name] = normalized_reply
        step_index += 1

    if step_index < len(_STEP_FIELDS):
        project_idea_planning_store.update(answers=answers, step_index=step_index)
        return _STEP_FIELDS[step_index][1]

    project_idea_planning_store.clear()
    enriched_idea = _compose_enriched_idea(
        pending.base_idea,
        answers,
    )
    return analyze_project_idea_to_obsidian(
        idea=enriched_idea,
        title=pending.note_title,
    )


def has_pending_project_idea_clarification() -> bool:
    return project_idea_planning_store.get() is not None


def _is_idea_incomplete(idea: str) -> bool:
    text = " ".join(str(idea or "").split())
    if len(text) < 45:
        return True
    word_count = len(text.split())
    if word_count < 7:
        return True
    return False


def _compose_enriched_idea(base_idea: str, answers: dict[str, str]) -> str:
    lines: list[str] = [f"Базовая идея: {base_idea}"]
    audience = answers.get("audience")
    platform = answers.get("platform")
    goal = answers.get("goal")
    if audience:
        lines.append(f"Целевая аудитория: {audience}")
    if platform:
        lines.append(f"Платформа старта: {platform}")
    if goal:
        lines.append(f"Ключевой результат первых недель: {goal}")
    return "\n".join(lines)
