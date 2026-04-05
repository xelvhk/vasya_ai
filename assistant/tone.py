from __future__ import annotations

import re
from dataclasses import dataclass


ConversationTone = str


@dataclass
class ToneSnapshot:
    tone: ConversationTone = "neutral"
    turns_left: int = 0


class ConversationToneMemory:
    def __init__(self) -> None:
        self._snapshot = ToneSnapshot()

    def observe_user_text(self, user_text: str) -> ConversationTone:
        normalized = " ".join(user_text.lower().strip().split())
        inferred = _infer_tone(normalized)
        if inferred is not None:
            self._snapshot = ToneSnapshot(
                tone=inferred,
                turns_left=_duration_for_tone(inferred),
            )
            return self._snapshot.tone

        if self._snapshot.turns_left > 0:
            self._snapshot.turns_left -= 1
        if self._snapshot.turns_left <= 0:
            self._snapshot = ToneSnapshot()
        return self._snapshot.tone

    def current(self) -> ConversationTone:
        return self._snapshot.tone


def _infer_tone(text: str) -> ConversationTone | None:
    if not text:
        return None

    if re.search(r"\b(грустно|печально|устал|устала|страшно|поддержи|злюсь|тяжело|сложно|боюсь|раздражает|бесит)\b", text):
        return "supportive"

    if re.search(r"\b(игра|поигра|скучно|загадк|угадай|прятки)\b", text):
        return "playful"

    if re.search(r"\b(привет|добрый|спасибо|мне нравится|ты мне нравишься|молодец|умница|класс|супер|здорово)\b", text):
        return "warm"

    return None


def _duration_for_tone(tone: ConversationTone) -> int:
    if tone == "supportive":
        return 5
    if tone == "playful":
        return 3
    if tone == "warm":
        return 3
    return 0


conversation_tone = ConversationToneMemory()
