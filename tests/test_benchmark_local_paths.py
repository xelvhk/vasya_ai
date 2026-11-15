from __future__ import annotations

import json
from unittest.mock import patch

from scripts.benchmark_local_paths import (
    NOTE, build_grounded_prompt, percentile, run_model_case, summarize,
)


def test_percentiles_and_errors_use_successful_runs() -> None:
    samples = [
        {"ok": True, "first_text_ms": 100.0, "total_ms": 200.0, "loaded_model_bytes": 100, "quality_ok": True},
        {"ok": True, "first_text_ms": 300.0, "total_ms": 400.0, "loaded_model_bytes": 120, "quality_ok": False},
        {"ok": False, "first_text_ms": None, "total_ms": 900.0, "loaded_model_bytes": None, "quality_ok": False},
    ]
    result = summarize(samples)
    assert result["errors"] == 1
    assert result["first_text_ms_p50"] == 300.0
    assert result["total_ms_p95"] == 400.0
    assert result["loaded_model_bytes_peak"] == 120
    assert percentile([], 0.95) is None


def test_note_case_uses_synthetic_evidence() -> None:
    prompt = build_grounded_prompt("Какой следующий шаг?", (NOTE,))
    assert NOTE.excerpt in prompt
    assert "Вопрос:" in prompt


def test_stream_case_records_first_text_and_validates_grounded_quote() -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def raise_for_status(self):
            return None

        def iter_lines(self):
            answer = json.dumps({"answer": "Проверить резервную копию.", "source": 1,
                                 "quote": "проверить резервное копирование на чистой установке"}, ensure_ascii=False)
            yield json.dumps({"response": answer}).encode()
            yield b'{"done":true}'

    with patch("scripts.benchmark_local_paths.requests.post", return_value=FakeResponse()), patch(
        "scripts.benchmark_local_paths.loaded_model_bytes", return_value=512
    ), patch("scripts.benchmark_local_paths.time.perf_counter", side_effect=[0.0, 0.1, 0.2]):
        result = run_model_case("http://127.0.0.1:11434/api/generate", "test-model", "prompt", grounded=True)
    assert result["ok"] is True
    assert result["quality_ok"] is True
    assert result["first_text_ms"] == 100.0
    assert result["total_ms"] == 200.0
