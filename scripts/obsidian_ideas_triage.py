from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.obsidian_knowledge_service import triage_unstructured_ideas


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify and normalize unstructured Obsidian ideas.")
    parser.add_argument("--vault", required=True, help="Absolute path to Obsidian vault.")
    parser.add_argument(
        "--ideas-dir",
        default="03_Knowledge/Неразобранные идеи",
        help="Ideas directory relative to vault.",
    )
    args = parser.parse_args()

    result = triage_unstructured_ideas(
        Path(args.vault).expanduser(),
        ideas_dir=str(args.ideas_dir),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
