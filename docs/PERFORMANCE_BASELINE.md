# Local performance baseline protocol

Run on the target Mac with an already installed Ollama model. Use the same
model, power mode, Ollama version, warm-run count, and background workload for
before/after comparisons. This script uses only synthetic Russian prompts and
does not read personal notes or voice logs.

```bash
.venv/bin/python scripts/benchmark_local_paths.py --model llama3:latest --warm-runs 5 --output build/benchmarks/local-paths.json
```

By default, the script unloads the selected model before each initial run to
measure cold loading. This briefly affects other Ollama clients. Use
`--no-cold` when that is undesirable. The JSON records first text and full
response times, warm p50/p95, errors, a simple output-quality check, and the
loaded model size reported by Ollama. At least five warm runs make p95 less
fragile; repeated runs on different days are preferable to one result.

The short-command case measures local intent detection. The long-chat and
grounded-note cases use the same prompt builders as production, but call
Ollama directly to measure streaming model latency. They do not include
microphone capture, STT, TTS, UI rendering, or disk indexing. For real voice
latency, use Vasya's existing speed report and compare its capture, STT,
intent, TTS, first-response, p95, and failure metrics on the same device. Do not
publish personal interaction logs.

Accept a speed change only when p50/p95 improve on the affected path while
the existing routing and grounding tests stay green. Record the model, prompt
settings, before/after JSON summaries, and any quality regressions in the
release note. The October 2026 model comparisons were exploratory and are
not a current baseline for a different Mac or model revision.
