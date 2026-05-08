from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.obsidian_knowledge_service import (
    audit_metadata_standards,
    autofix_metadata_standards,
    build_vault_health_report,
    ensure_navigation_scaffold,
    write_vault_health_note,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Systematize Obsidian vault metadata and navigation.")
    parser.add_argument("--vault", required=True, help="Absolute path to Obsidian vault.")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Default is dry-run.")
    parser.add_argument("--fix-limit", type=int, default=500, help="Max notes to autofix in one run.")
    parser.add_argument("--with-health", action="store_true", help="Build vault health report and note.")
    parser.add_argument("--stale-days", type=int, default=30, help="Threshold for stale notes.")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser()
    dry_run = not args.apply

    before = audit_metadata_standards(vault)
    scaffold = ensure_navigation_scaffold(vault, dry_run=dry_run)
    fix = autofix_metadata_standards(vault, dry_run=dry_run, limit=max(1, int(args.fix_limit)))
    health_preview = build_vault_health_report(vault, stale_days=max(1, int(args.stale_days))) if args.with_health else None
    health_note = (
        write_vault_health_note(vault, stale_days=max(1, int(args.stale_days)))
        if args.with_health and args.apply
        else None
    )
    after = audit_metadata_standards(vault) if args.apply else None

    print(
        json.dumps(
            {
                "before": before,
                "scaffold": scaffold,
                "fix": fix,
                "health_preview": health_preview,
                "health_note": health_note,
                "after": after,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
