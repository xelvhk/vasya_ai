from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
LAUNCH_AGENT_LABEL = "com.vasya.ai"


def launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"


def is_autostart_enabled() -> bool:
    return launch_agent_path().exists()


def install_autostart() -> None:
    plist_path = launch_agent_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": [sys.executable, str(ROOT_DIR / "main.py")],
        "WorkingDirectory": str(ROOT_DIR),
        "RunAtLoad": True,
        "KeepAlive": False,
        "StandardOutPath": str(ROOT_DIR / "storage" / "launchagent.out.log"),
        "StandardErrorPath": str(ROOT_DIR / "storage" / "launchagent.err.log"),
    }
    with plist_path.open("wb") as handle:
        plistlib.dump(payload, handle)

    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(plist_path)], check=False)
    subprocess.run(["launchctl", "bootstrap", domain, str(plist_path)], check=True)


def uninstall_autostart() -> None:
    plist_path = launch_agent_path()
    domain = f"gui/{os.getuid()}"

    if plist_path.exists():
        subprocess.run(["launchctl", "bootout", domain, str(plist_path)], check=False)
        plist_path.unlink()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Manage Vasya macOS autostart")
    parser.add_argument("command", choices=["install", "uninstall", "status"])
    args = parser.parse_args()

    if args.command == "install":
        install_autostart()
        print(f"Installed autostart: {launch_agent_path()}")
        return
    if args.command == "uninstall":
        uninstall_autostart()
        print("Removed autostart")
        return

    print("enabled" if is_autostart_enabled() else "disabled")


if __name__ == "__main__":
    main()
