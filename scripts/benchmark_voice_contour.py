from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from services.benchmark_service import build_benchmark_snapshot, build_benchmark_text_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark harness for Vasya voice/pipeline metrics.")
    parser.add_argument("--limit", type=int, default=80, help="How many recent interaction rows to analyze.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    args = parser.parse_args()

    if args.json:
        print(json.dumps(build_benchmark_snapshot(limit=args.limit), ensure_ascii=False, indent=2))
        return
    print(build_benchmark_text_report(limit=args.limit))


if __name__ == "__main__":
    main()
