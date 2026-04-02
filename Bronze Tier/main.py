"""
AI Employee — Bronze Tier Orchestrator
=======================================
Entry point for the Personal AI Employee system.

Usage:
    uv run main.py                  # Start filesystem watcher
    uv run main.py --status         # Show vault status
    uv run main.py --help           # Show help
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

VAULT_PATH = Path(__file__).parent / "AI_Employee_Vault"


def show_status():
    """Print current vault status to terminal."""
    inbox = VAULT_PATH / "Inbox"
    needs_action = VAULT_PATH / "Needs_Action"
    done = VAULT_PATH / "Done"
    logs = VAULT_PATH / "Logs"

    def count_files(folder: Path) -> int:
        return len([f for f in folder.iterdir() if f.is_file() and f.name != ".gitkeep"])

    print("\n" + "=" * 50)
    print("  AI Employee — Bronze Tier — Status")
    print("=" * 50)
    print(f"  Vault     : {VAULT_PATH}")
    print(f"  Inbox     : {count_files(inbox)} files")
    print(f"  Needs Action: {count_files(needs_action)} files")
    print(f"  Done      : {count_files(done)} files")
    print(f"  Logs      : {count_files(logs)} files")
    print("=" * 50 + "\n")


def update_dashboard():
    """Update Dashboard.md with current vault stats."""
    inbox = VAULT_PATH / "Inbox"
    needs_action = VAULT_PATH / "Needs_Action"
    done = VAULT_PATH / "Done"

    def count_files(folder: Path) -> int:
        return len([f for f in folder.iterdir() if f.is_file() and f.name != ".gitkeep"])

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dashboard = VAULT_PATH / "Dashboard.md"

    content = f"""# AI Employee Dashboard
---
last_updated: {now}
status: active
---

## System Status
| Component | Status |
|-----------|--------|
| Filesystem Watcher | Running |
| Vault Read/Write | Active |
| Agent Skills | Loaded |

## Inbox Summary
- **Inbox**: {count_files(inbox)} files waiting
- **Needs Action**: {count_files(needs_action)} files
- **Completed**: {count_files(done)} files total

## Quick Stats
| Folder | Count |
|--------|-------|
| /Inbox | {count_files(inbox)} |
| /Needs_Action | {count_files(needs_action)} |
| /Done | {count_files(done)} |

---
*Updated by AI Employee — {now}*
"""
    dashboard.write_text(content)
    print(f"Dashboard updated at {now}")


def start_watcher():
    """Start the filesystem watcher."""
    from watchers.filesystem_watcher import FilesystemWatcher
    watcher = FilesystemWatcher(str(VAULT_PATH))
    watcher.run()


def main():
    parser = argparse.ArgumentParser(
        description="AI Employee — Bronze Tier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  (no args)       Start filesystem watcher
  --status        Show vault status
  --update-dash   Update Dashboard.md
        """,
    )
    parser.add_argument("--status", action="store_true", help="Show vault status")
    parser.add_argument("--update-dash", action="store_true", help="Update Dashboard.md")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.update_dash:
        update_dashboard()
    else:
        print("Starting AI Employee Filesystem Watcher...")
        start_watcher()


if __name__ == "__main__":
    main()
