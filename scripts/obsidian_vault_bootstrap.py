from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.obsidian_knowledge_service import (
    bootstrap_managed_vault,
    build_vault_index,
    setup_recommended_plugins,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap managed Obsidian vault for Vasya AI.")
    parser.add_argument("--vault", required=True, help="Absolute path to Obsidian vault.")
    parser.add_argument("--with-plugins", action="store_true", help="Write recommended community plugin list.")
    parser.add_argument("--index", action="store_true", help="Build metadata/link index after bootstrap.")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser()
    result = {"bootstrap": bootstrap_managed_vault(vault)}

    if args.with_plugins:
        result["plugins"] = setup_recommended_plugins(vault)
    if args.index:
        result["index"] = build_vault_index(vault)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
