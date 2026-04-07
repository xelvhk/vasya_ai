from __future__ import annotations

from core.models import IntentResult


_MEETING_MARKERS = (
    "встреч",
    "созвон",
    "митинг",
    "звонок",
    "колл",
    "call",
    "meet",
)

_BOTH_TASKS_AND_EVENTS_MARKERS = (
    "задач и дела",
    "задачи и дела",
    "задач и событий",
    "задачи и события",
    "дела и задачи",
    "события и задачи",
)


def build_handoffs(intent_result: IntentResult, user_text: str) -> list[IntentResult]:
    normalized = " ".join(user_text.lower().strip().split())
    if not normalized:
        return []

    handoffs: list[IntentResult] = []

    # task_agent -> calendar_agent
    if intent_result.intent == "create_task":
        task_text = str(intent_result.data.get("task", "")).strip()
        dt_text = intent_result.data.get("datetime")
        if (
            task_text
            and isinstance(dt_text, str)
            and dt_text.strip()
            and any(marker in task_text.lower() for marker in _MEETING_MARKERS)
        ):
            handoffs.append(
                IntentResult(
                    intent="create_event",
                    data={
                        "title": task_text,
                        "datetime": dt_text,
                    },
                )
            )

    # Combined view requests: include tasks + events together.
    if intent_result.intent == "get_tasks":
        if any(marker in normalized for marker in _BOTH_TASKS_AND_EVENTS_MARKERS):
            handoffs.append(
                IntentResult(
                    intent="get_events",
                    data={"datetime": intent_result.data.get("datetime")},
                )
            )

    if intent_result.intent == "get_events":
        if any(marker in normalized for marker in _BOTH_TASKS_AND_EVENTS_MARKERS):
            handoffs.append(
                IntentResult(
                    intent="get_tasks",
                    data={"datetime": intent_result.data.get("datetime")},
                )
            )

    return handoffs

