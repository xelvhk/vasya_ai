from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.obsidian_knowledge_service import (
    build_graph_connectivity_report,
    strengthen_graph_links,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze and strengthen Obsidian graph links.")
    parser.add_argument("--vault", required=True, help="Absolute path to Obsidian vault.")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Default is dry-run.")
    parser.add_argument("--limit", type=int, default=100, help="Max notes to update in one run.")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser()
    report_before = build_graph_connectivity_report(vault)
    strengthen = strengthen_graph_links(vault, dry_run=not args.apply, limit=max(1, int(args.limit)))
    report_after = build_graph_connectivity_report(vault) if args.apply else None

    result = {
        "before": report_before,
        "strengthen": strengthen,
        "after": report_after,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
