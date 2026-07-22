from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemorySearchAction:
    label: str
    kind: str
    target: str


def memory_search_actions(result: dict, *, limit: int = 8) -> list[MemorySearchAction]:
    items = result.get("items")
    if not isinstance(items, list) or not items:
        return []

    actions: list[MemorySearchAction] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Untitled memory").strip()
        short_title = title if len(title) <= 42 else f"{title[:39].rstrip()}..."
        markdown_path = str(item.get("markdown_path") or "").strip()
        url = str(item.get("url") or "").strip()
        if markdown_path:
            actions.append(MemorySearchAction(f"Файл: {short_title}", "file", markdown_path))
        if url:
            actions.append(MemorySearchAction(f"URL: {short_title}", "url", url))
    return actions


def selected_memory_search_action(
    actions: list[MemorySearchAction],
    selected_label: str,
) -> MemorySearchAction | None:
    for action in actions:
        if action.label == selected_label:
            return action
    return None
