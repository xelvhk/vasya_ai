from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.obsidian_knowledge_service import rename_idea_notes_from_content


def main() -> None:
    parser = argparse.ArgumentParser(description="Rename Obsidian idea notes based on note content.")
    parser.add_argument("--vault", required=True, help="Absolute path to Obsidian vault.")
    parser.add_argument(
        "--ideas-dir",
        default="03_Knowledge/Неразобранные идеи",
        help="Ideas directory relative to vault.",
    )
    parser.add_argument("--apply", action="store_true", help="Apply renames. Default is dry-run.")
    parser.add_argument("--limit", type=int, default=200, help="Max notes to process.")
    args = parser.parse_args()

    result = rename_idea_notes_from_content(
        Path(args.vault).expanduser(),
        ideas_dir=str(args.ideas_dir),
        dry_run=not args.apply,
        limit=max(1, int(args.limit)),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
