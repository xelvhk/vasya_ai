"""Synthetic local-path benchmark; never reads personal notes or voice logs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import OLLAMA_CHAT_NUM_PREDICT, OLLAMA_CHAT_TEMPERATURE, OLLAMA_URL  # noqa: E402
from services.allowed_knowledge_service import KnowledgeHit  # noqa: E402
from services.chat_service import _build_chat_prompt  # noqa: E402
from services.grounded_knowledge_answer_service import build_grounded_prompt  # noqa: E402
from utils.intent_fastpaths import detect_fast_intent  # noqa: E402


NOTE = KnowledgeHit(
    relative_path="synthetic/example.md",
    title="Учебный проект",
    excerpt="В учебном проекте следующий шаг — проверить резервное копирование на чистой установке.",
    url="",
    modified_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)
SHORT_COMMAND = "Что дальше по проектам?"
LONG_QUESTION = "Объясни на русском языке, как проверить выпуск локального приложения: тесты, резервная копия, обновление и откат."
NOTE_QUESTION = "Какой следующий шаг в учебном проекте?"


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percent + 0.999999)))
    return round(ordered[index], 1)


def summarize(samples: list[dict]) -> dict:
    successful = [sample for sample in samples if sample["ok"]]
    memory_values = [s["loaded_model_bytes"] for s in samples if s["loaded_model_bytes"] is not None]
    return {
        "runs": len(samples),
        "errors": len(samples) - len(successful),
        "first_text_ms_p50": percentile([s["first_text_ms"] for s in successful], 0.50),
        "first_text_ms_p95": percentile([s["first_text_ms"] for s in successful], 0.95),
        "total_ms_p50": percentile([s["total_ms"] for s in successful], 0.50),
        "total_ms_p95": percentile([s["total_ms"] for s in successful], 0.95),
        "loaded_model_bytes_peak": max(memory_values) if memory_values else None,
        "quality_passes": sum(bool(s.get("quality_ok")) for s in samples),
    }


def loaded_model_bytes(base_url: str, model: str) -> int | None:
    try:
        response = requests.get(base_url + "/api/ps", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        return sum(int(item.get("size", 0)) for item in models if item.get("name") == model)
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        return None


def unload_model(generate_url: str, model: str) -> None:
    response = requests.post(
        generate_url, json={"model": model, "prompt": "", "stream": False, "keep_alive": 0}, timeout=30,
    )
    response.raise_for_status()


def run_model_case(generate_url: str, model: str, prompt: str, *, grounded: bool) -> dict:
    started = time.perf_counter()
    first_text_ms = None
    parts: list[str] = []
    error = None
    try:
        with requests.post(
            generate_url,
            json={"model": model, "prompt": prompt, "stream": True, "think": False,
                  "options": {"temperature": 0 if grounded else OLLAMA_CHAT_TEMPERATURE,
                              "num_predict": 320 if grounded else OLLAMA_CHAT_NUM_PREDICT}},
            stream=True, timeout=180,
        ) as response:
            response.raise_for_status()
            finished = False
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                chunk = data.get("response", "")
                if chunk:
                    if first_text_ms is None:
                        first_text_ms = round((time.perf_counter() - started) * 1000, 1)
                    parts.append(chunk)
                if data.get("done"):
                    finished = True
                    break
            if not finished:
                error = "stream_incomplete"
    except (requests.RequestException, ValueError, TypeError) as exc:
        error = type(exc).__name__
    total_ms = round((time.perf_counter() - started) * 1000, 1)
    answer = "".join(parts).strip()
    if not answer and error is None:
        error = "empty_response"
    quality_ok = bool(answer) and not grounded and error is None
    if grounded and answer and error is None:
        try:
            parsed = json.loads(answer)
            quality_ok = (
                isinstance(parsed.get("answer"), str)
                and parsed.get("source") == 1
                and isinstance(parsed.get("quote"), str)
                and len(parsed["quote"].strip()) >= 12
                and parsed["quote"].strip() in NOTE.excerpt
            )
        except (ValueError, TypeError, AttributeError):
            quality_ok = False
    base_url = generate_url.rsplit("/api/generate", 1)[0]
    return {
        "ok": error is None,
        "error": error,
        "first_text_ms": first_text_ms,
        "total_ms": total_ms,
        "loaded_model_bytes": loaded_model_bytes(base_url, model),
        "quality_ok": quality_ok,
    }


def run_benchmark(model: str, warm_runs: int, *, include_cold: bool) -> dict:
    parsed_url = urlparse(OLLAMA_URL)
    if parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"} or not OLLAMA_URL.endswith("/api/generate"):
        raise ValueError("Benchmark requires a local Ollama /api/generate endpoint")
    fast_samples = []
    for _ in range(warm_runs + 1):
        started = time.perf_counter()
        result = detect_fast_intent(SHORT_COMMAND)
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        fast_samples.append({"ok": result is not None and result.intent == "project_status_summary",
                             "first_text_ms": elapsed, "total_ms": elapsed, "loaded_model_bytes": 0,
                             "quality_ok": result is not None and result.intent == "project_status_summary"})

    cases = {
        "long_chat": _build_chat_prompt(LONG_QUESTION, allow_greeting=False, tone="neutral", child_mode=False),
        "grounded_note": build_grounded_prompt(NOTE_QUESTION, (NOTE,)),
    }
    results = {"short_command": {"warm": summarize(fast_samples)}}
    for name, prompt in cases.items():
        cold = None
        if include_cold:
            unload_model(OLLAMA_URL, model)
            cold = run_model_case(OLLAMA_URL, model, prompt, grounded=name == "grounded_note")
        warm = [run_model_case(OLLAMA_URL, model, prompt, grounded=name == "grounded_note")
                for _ in range(warm_runs)]
        results[name] = {"cold": cold, "warm": summarize(warm)}
    return {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "model": model,
        "warm_runs": warm_runs,
        "cases": results,
        "note": "Synthetic model/path benchmark; memory is loaded Ollama model bytes, not total process RAM. Voice capture, STT, TTS and end-to-end UI are not measured.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Already installed local Ollama model")
    parser.add_argument("--warm-runs", type=int, default=5)
    parser.add_argument("--no-cold", action="store_true", help="Do not unload the model before initial runs")
    parser.add_argument("--output", type=Path, help="Optional JSON result file")
    args = parser.parse_args()
    if not 1 <= args.warm_runs <= 30:
        parser.error("--warm-runs must be between 1 and 30")
    try:
        result = run_benchmark(args.model, args.warm_runs, include_cold=not args.no_cold)
    except (ValueError, requests.RequestException) as exc:
        parser.exit(1, f"Benchmark failed: {exc}\n")
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
