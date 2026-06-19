from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.tts_benchmark_service import (  # noqa: E402
    DEFAULT_TTS_BENCHMARK_TEXT,
    build_tts_benchmark_report,
    run_tts_benchmark,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Vasya TTS backend synthesis latency.")
    parser.add_argument("--text", default=DEFAULT_TTS_BENCHMARK_TEXT, help="Text to synthesize.")
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Backend to benchmark. Can be repeated. Defaults to say, piper, hybrid, xtts.",
    )
    parser.add_argument("--include-heavy", action="store_true", help="Run heavy backends such as XTTS.")
    parser.add_argument(
        "--include-experimental",
        action="store_true",
        help="Include experimental placeholder rows such as MisoTTS.",
    )
    parser.add_argument("--save-artifacts", action="store_true", help="Keep generated audio files.")
    parser.add_argument(
        "--artifact-dir",
        default="storage/tts_benchmarks",
        help="Directory for generated audio when --save-artifacts is enabled.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    args = parser.parse_args()

    snapshot = run_tts_benchmark(
        text=args.text,
        backends=args.backends,
        include_heavy=args.include_heavy,
        include_experimental=args.include_experimental,
        save_artifacts=args.save_artifacts,
        artifact_dir=Path(args.artifact_dir),
    )
    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return
    print(build_tts_benchmark_report(snapshot))


if __name__ == "__main__":
    main()
