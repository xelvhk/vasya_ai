from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config.app_paths import (  # noqa: E402
    MigrationResult,
    migrate_legacy_runtime_data,
    resolve_app_paths,
)


def run_migration(
    legacy_root: Path,
    *,
    app_data_dir: Path | None = None,
) -> MigrationResult:
    environ = dict(os.environ)
    if app_data_dir is not None:
        environ["VASYA_APP_DATA_DIR"] = str(app_data_dir)
    paths = resolve_app_paths(
        environ=environ,
        packaged=True,
        source_root=ROOT_DIR,
    )
    return migrate_legacy_runtime_data(Path(legacy_root), paths)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy legacy Vasya runtime data into the platform app-data profile."
    )
    parser.add_argument(
        "--legacy-root",
        type=Path,
        required=True,
        help="Old Vasya checkout or launch directory containing .env and storage/.",
    )
    parser.add_argument(
        "--app-data-dir",
        type=Path,
        help="Optional destination override; defaults to the current platform profile.",
    )
    args = parser.parse_args()

    result = run_migration(
        args.legacy_root,
        app_data_dir=args.app_data_dir,
    )
    print(f"Copied files: {len(result.copied)}")
    print(f"Preserved existing files: {len(result.skipped)}")
    for path in result.copied:
        print(f"  copied: {path}")
    for path in result.skipped:
        print(f"  kept: {path}")


if __name__ == "__main__":
    main()
