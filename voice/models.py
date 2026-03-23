from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None
    avg_logprob: float | None
    no_speech_prob: float | None

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()
