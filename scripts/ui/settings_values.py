from __future__ import annotations


def minimum_noisy_rms_threshold(quiet_threshold: float) -> float:
    return float(quiet_threshold) + 20.0


def applied_noisy_rms_threshold(quiet_threshold: float, noisy_threshold: float) -> float:
    quiet = float(quiet_threshold)
    noisy = float(noisy_threshold)
    if noisy <= quiet:
        return minimum_noisy_rms_threshold(quiet)
    return noisy
