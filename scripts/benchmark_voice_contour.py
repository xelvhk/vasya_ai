from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from services.benchmark_service import build_benchmark_snapshot, build_benchmark_text_report


def _extract(snapshot: dict[str, object], group: str, key: str) -> float:
    payload = snapshot.get(group)
    if not isinstance(payload, dict):
        return 0.0
    value = payload.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _check_regression(
    current: dict[str, object],
    baseline: dict[str, object],
    *,
    max_ttfr_regression_ms: float,
    max_tta_regression_ms: float,
    max_pipeline_ttfr_regression_ms: float,
    max_false_barge_regression_pct: float,
) -> tuple[bool, list[str]]:
    issues: list[str] = []

    current_voice_ttfr = _extract(current, "voice", "ttfr_avg_ms")
    baseline_voice_ttfr = _extract(baseline, "voice", "ttfr_avg_ms")
    if current_voice_ttfr - baseline_voice_ttfr > max_ttfr_regression_ms:
        issues.append(
            f"voice TTFR regression: {current_voice_ttfr:.1f} ms vs baseline {baseline_voice_ttfr:.1f} ms"
        )

    current_voice_tta = _extract(current, "voice", "tta_avg_ms")
    baseline_voice_tta = _extract(baseline, "voice", "tta_avg_ms")
    if current_voice_tta - baseline_voice_tta > max_tta_regression_ms:
        issues.append(
            f"voice TTA regression: {current_voice_tta:.1f} ms vs baseline {baseline_voice_tta:.1f} ms"
        )

    current_pipe_ttfr = _extract(current, "pipeline", "ttfr_avg_ms")
    baseline_pipe_ttfr = _extract(baseline, "pipeline", "ttfr_avg_ms")
    if current_pipe_ttfr - baseline_pipe_ttfr > max_pipeline_ttfr_regression_ms:
        issues.append(
            f"pipeline TTFR regression: {current_pipe_ttfr:.1f} ms vs baseline {baseline_pipe_ttfr:.1f} ms"
        )

    current_false_barge = _extract(current, "voice", "false_barge_rate_pct")
    baseline_false_barge = _extract(baseline, "voice", "false_barge_rate_pct")
    if current_false_barge - baseline_false_barge > max_false_barge_regression_pct:
        issues.append(
            "false barge-in regression: "
            f"{current_false_barge:.2f}% vs baseline {baseline_false_barge:.2f}%"
        )

    return (not issues), issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark harness for Vasya voice/pipeline metrics.")
    parser.add_argument("--limit", type=int, default=80, help="How many recent interaction rows to analyze.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    parser.add_argument(
        "--baseline-file",
        default="storage/benchmark_baseline.json",
        help="Path to benchmark baseline JSON file.",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save current snapshot as new baseline and exit.",
    )
    parser.add_argument(
        "--check-regression",
        action="store_true",
        help="Compare current snapshot with baseline and exit with code 1 on regression.",
    )
    parser.add_argument(
        "--max-ttfr-regression-ms",
        type=float,
        default=200.0,
        help="Allowed regression for voice TTFR average in milliseconds.",
    )
    parser.add_argument(
        "--max-tta-regression-ms",
        type=float,
        default=300.0,
        help="Allowed regression for voice TTA average in milliseconds.",
    )
    parser.add_argument(
        "--max-pipeline-ttfr-regression-ms",
        type=float,
        default=120.0,
        help="Allowed regression for pipeline TTFR average in milliseconds.",
    )
    parser.add_argument(
        "--max-false-barge-regression-pct",
        type=float,
        default=3.0,
        help="Allowed regression for false barge-in rate in percentage points.",
    )
    args = parser.parse_args()

    snapshot = build_benchmark_snapshot(limit=args.limit)
    baseline_path = Path(args.baseline_file)

    if args.save_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Saved benchmark baseline to {baseline_path}")
        return

    if args.check_regression:
        if not baseline_path.exists():
            print(
                f"Baseline file not found: {baseline_path}. "
                "Run with --save-baseline first.",
                file=sys.stderr,
            )
            raise SystemExit(2)
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        ok, issues = _check_regression(
            snapshot,
            baseline,
            max_ttfr_regression_ms=float(args.max_ttfr_regression_ms),
            max_tta_regression_ms=float(args.max_tta_regression_ms),
            max_pipeline_ttfr_regression_ms=float(args.max_pipeline_ttfr_regression_ms),
            max_false_barge_regression_pct=float(args.max_false_barge_regression_pct),
        )
        if args.json:
            print(
                json.dumps(
                    {"ok": ok, "issues": issues, "current": snapshot, "baseline": baseline},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(build_benchmark_text_report(limit=args.limit))
            print(f"Regression check: {'OK' if ok else 'FAILED'}")
            for issue in issues:
                print(f"- {issue}")
        raise SystemExit(0 if ok else 1)

    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return
    print(build_benchmark_text_report(limit=args.limit))


if __name__ == "__main__":
    main()
