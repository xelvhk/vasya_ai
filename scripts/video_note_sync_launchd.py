"""Build a macOS LaunchAgent for periodic server-to-Obsidian video note sync."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

from scripts.sync_video_notes import read_api_key_file, validate_server_url


LABEL = "com.vasya.video-note-sync"
REPO = Path(__file__).absolute().parent.parent


def build_launch_agent(
    *, server: str, vault: Path, api_key_file: Path, python: Path,
    repo: Path, logs: Path, interval: int = 300,
) -> dict:
    if interval < 60:
        raise ValueError("Sync interval must be at least 60 seconds")
    server = validate_server_url(server)
    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(python), "-m", "scripts.sync_video_notes", "--server", server,
            "--vault", str(vault), "--api-key-file", str(api_key_file),
        ],
        "WorkingDirectory": str(repo),
        "RunAtLoad": True,
        "StartInterval": interval,
        "ProcessType": "Background",
        "StandardOutPath": str(logs / "video-note-sync.out.log"),
        "StandardErrorPath": str(logs / "video-note-sync.err.log"),
    }


def launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def install_launch_agent(payload: dict, plist_path: Path, api_key_file: Path) -> None:
    read_api_key_file(api_key_file)
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    log_dir = Path(payload["StandardOutPath"]).parent
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_dir.chmod(0o700)
    with plist_path.open("xb") as handle:
        os.fchmod(handle.fileno(), 0o600)
        plistlib.dump(payload, handle)
    try:
        subprocess.run(
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)], check=True
        )
    except (OSError, subprocess.CalledProcessError):
        plist_path.unlink()
        raise


def uninstall_launch_agent(plist_path: Path) -> None:
    if not plist_path.exists():
        return
    subprocess.run(
        ["launchctl", "bootout", f"gui/{os.getuid()}", str(plist_path)], check=False
    )
    plist_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("render", "install"):
        command = subcommands.add_parser(name)
        command.add_argument("--server", required=True)
        command.add_argument("--vault", type=Path, required=True)
        command.add_argument("--api-key-file", type=Path, required=True)
        command.add_argument("--interval", type=int, default=300)
        command.add_argument("--logs", type=Path, default=Path.home() / "Library/Logs/Vasya")
    subcommands.add_parser("uninstall")
    args = parser.parse_args()
    plist_path = launch_agent_path()
    if args.command == "uninstall":
        uninstall_launch_agent(plist_path)
        print(f"Removed {plist_path}")
        return 0

    api_key_file = args.api_key_file.expanduser().absolute()
    payload = build_launch_agent(
        server=args.server, vault=args.vault.expanduser().absolute(),
        api_key_file=api_key_file, python=Path(sys.executable).absolute(),
        repo=REPO, logs=args.logs.expanduser().absolute(), interval=args.interval,
    )
    if args.command == "render":
        sys.stdout.buffer.write(plistlib.dumps(payload))
        return 0
    install_launch_agent(payload, plist_path, api_key_file)
    print(f"Installed {plist_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
