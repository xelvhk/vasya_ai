from __future__ import annotations


def normalize_hotkey_combination(combination: str) -> str:
    normalized = combination.strip()
    normalized = normalized.replace("+space", "+<space>")
    normalized = normalized.replace("<space>>", "<space>")
    return normalized
