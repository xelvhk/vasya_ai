from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from config.settings import USER_PROFILE_STATE_FILE


@dataclass
class UserProfileSnapshot:
    name: str | None = None
    likes: list[str] = field(default_factory=list)
    dislikes: list[str] = field(default_factory=list)
    preferred_style: str | None = None
    facts: list[str] = field(default_factory=list)


class UserProfileMemory:
    def __init__(self, state_file: str) -> None:
        self._state_path = Path(state_file)
        self._snapshot = self._load()

    def observe_user_text(self, user_text: str) -> None:
        normalized = " ".join(user_text.strip().split())
        if not normalized:
            return

        changed = False
        changed |= self._capture_name(normalized)
        changed |= self._capture_preferences(normalized)
        changed |= self._capture_style(normalized)
        if changed:
            self._save()

    def render_hint(self) -> str | None:
        chunks: list[str] = []
        if self._snapshot.name:
            chunks.append(f"Имя пользователя: {self._snapshot.name}.")
        if self._snapshot.likes:
            chunks.append(f"Нравится: {', '.join(self._snapshot.likes[:4])}.")
        if self._snapshot.dislikes:
            chunks.append(f"Не нравится: {', '.join(self._snapshot.dislikes[:4])}.")
        if self._snapshot.preferred_style:
            chunks.append(f"Предпочитаемый стиль: {self._snapshot.preferred_style}.")
        if self._snapshot.facts:
            chunks.append(f"Факты о пользователе: {', '.join(self._snapshot.facts[:4])}.")
        if not chunks:
            return None
        return " ".join(chunks)

    def remember_explicit(self, text: str) -> bool:
        normalized = _normalize_phrase(text)
        if not normalized:
            return False

        changed = False
        name_changed = self._capture_name(normalized)
        pref_changed = self._capture_preferences(normalized)
        style_changed = self._capture_style(normalized)
        changed |= name_changed or pref_changed or style_changed
        if not (name_changed or pref_changed or style_changed):
            changed |= _append_unique(self._snapshot.facts, normalized, max_items=12)
        if changed:
            self._save()
        return changed

    def forget_explicit(self, target: str) -> bool:
        normalized = _normalize_phrase(target).casefold()
        if not normalized:
            return False

        if normalized in {
            "все",
            "всё",
            "все это",
            "всё это",
            "всю память",
            "все что помнишь",
            "всё что помнишь",
            "обо мне все",
        }:
            if self._is_empty():
                return False
            self._snapshot = UserProfileSnapshot()
            self._save()
            return True

        if normalized in {"это", "это все", "последнее", "последнее это"}:
            if self._snapshot.facts:
                self._snapshot.facts.pop()
                self._save()
                return True
            return False

        changed = False
        changed |= _remove_matching(self._snapshot.likes, normalized)
        changed |= _remove_matching(self._snapshot.dislikes, normalized)
        changed |= _remove_matching(self._snapshot.facts, normalized)

        if self._snapshot.name and _contains_either(self._snapshot.name, normalized):
            self._snapshot.name = None
            changed = True

        if (
            self._snapshot.preferred_style
            and _contains_either(self._snapshot.preferred_style, normalized)
        ):
            self._snapshot.preferred_style = None
            changed = True

        if changed:
            self._save()
        return changed

    def summary_text(self) -> str:
        chunks: list[str] = []
        if self._snapshot.name:
            chunks.append(f"Помню, что тебя зовут {self._snapshot.name}.")
        if self._snapshot.likes:
            chunks.append(f"Тебе нравится: {', '.join(self._snapshot.likes[:4])}.")
        if self._snapshot.dislikes:
            chunks.append(f"Тебе не нравится: {', '.join(self._snapshot.dislikes[:4])}.")
        if self._snapshot.preferred_style:
            chunks.append(f"По стилю общения: {self._snapshot.preferred_style}.")
        if self._snapshot.facts:
            chunks.append(f"Еще помню: {', '.join(self._snapshot.facts[:4])}.")
        if not chunks:
            return "Пока почти ничего личного не запоминала."
        return " ".join(chunks)

    def clear_all(self) -> bool:
        if self._is_empty():
            return False
        self._snapshot = UserProfileSnapshot()
        self._save()
        return True

    def total_items(self) -> int:
        total = 0
        if self._snapshot.name:
            total += 1
        if self._snapshot.preferred_style:
            total += 1
        total += len(self._snapshot.likes)
        total += len(self._snapshot.dislikes)
        total += len(self._snapshot.facts)
        return total

    def _capture_name(self, text: str) -> bool:
        match = re.search(r"\bменя зовут\s+([а-яёa-z-]{2,24})\b", text, re.IGNORECASE)
        if not match:
            return False
        name = _normalize_phrase(match.group(1))
        if not name:
            return False
        if self._snapshot.name == name:
            return False
        self._snapshot.name = name
        return True

    def _capture_preferences(self, text: str) -> bool:
        changed = False
        positive = re.search(
            r"\b(?:мне нравится|я люблю|обожаю)\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        negative = re.search(
            r"\b(?:мне не нравится|я не люблю|терпеть не могу)\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if positive:
            item = _normalize_phrase(positive.group(1))
            if item:
                changed |= _append_unique(self._snapshot.likes, item, max_items=8)
        if negative:
            item = _normalize_phrase(negative.group(1))
            if item:
                changed |= _append_unique(self._snapshot.dislikes, item, max_items=8)
        return changed

    def _capture_style(self, text: str) -> bool:
        style_match = re.search(
            r"\b(?:будь|давай)\s+(.{3,80})$",
            text,
            re.IGNORECASE,
        )
        if not style_match:
            return False

        candidate = _normalize_phrase(style_match.group(1))
        if not candidate:
            return False

        style_markers = (
            "формаль",
            "неформаль",
            "короче",
            "дружелюб",
            "тепл",
            "сух",
            "строг",
            "весел",
            "шут",
            "спокой",
        )
        if not any(marker in candidate.lower() for marker in style_markers):
            return False

        if self._snapshot.preferred_style == candidate:
            return False
        self._snapshot.preferred_style = candidate
        return True

    def _load(self) -> UserProfileSnapshot:
        if not self._state_path.exists():
            return UserProfileSnapshot()
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return UserProfileSnapshot()

        if not isinstance(payload, dict):
            return UserProfileSnapshot()
        return UserProfileSnapshot(
            name=_safe_text(payload.get("name")),
            likes=_safe_list(payload.get("likes")),
            dislikes=_safe_list(payload.get("dislikes")),
            preferred_style=_safe_text(payload.get("preferred_style")),
            facts=_safe_list(payload.get("facts"), max_items=12),
        )

    def _save(self) -> None:
        payload = {
            "name": self._snapshot.name,
            "likes": self._snapshot.likes[:8],
            "dislikes": self._snapshot.dislikes[:8],
            "preferred_style": self._snapshot.preferred_style,
            "facts": self._snapshot.facts[:12],
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _is_empty(self) -> bool:
        return not any(
            (
                self._snapshot.name,
                self._snapshot.likes,
                self._snapshot.dislikes,
                self._snapshot.preferred_style,
                self._snapshot.facts,
            )
        )


def _append_unique(items: list[str], value: str, *, max_items: int) -> bool:
    normalized_existing = {item.casefold() for item in items}
    if value.casefold() in normalized_existing:
        return False
    items.append(value)
    if len(items) > max_items:
        del items[:-max_items]
    return True


def _normalize_phrase(text: str) -> str:
    cleaned = text.strip(" .,!?:;\"'").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:80]


def _safe_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = _normalize_phrase(value)
    return cleaned or None


def _safe_list(value: object, *, max_items: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            continue
        normalized = _normalize_phrase(raw)
        if normalized:
            _append_unique(items, normalized, max_items=max_items)
    return items[:max_items]


def _remove_matching(items: list[str], target: str) -> bool:
    original_len = len(items)
    items[:] = [item for item in items if not _contains_either(item, target)]
    return len(items) != original_len


def _contains_either(value: str, target: str) -> bool:
    left = value.casefold()
    right = target.casefold()
    return right in left or left in right


user_profile_memory = UserProfileMemory(USER_PROFILE_STATE_FILE)
