"""
Filesystem Watcher - Monitors the /Inbox folder.

When a new file is dropped into /Inbox, this watcher:
1. Detects the new file
2. Creates a structured .md action file in /Needs_Action
3. Logs the event

Usage:
    python watchers/filesystem_watcher.py
    python watchers/filesystem_watcher.py --vault /path/to/vault
"""

import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ORIGINAL_SYS_PATH = list(sys.path)
try:
    sys.path = [
        entry
        for entry in sys.path
        if Path(entry or ".").resolve() != PROJECT_ROOT
    ]
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
finally:
    sys.path = _ORIGINAL_SYS_PATH

# Add parent dir to path so we can import base_watcher
sys.path.insert(0, str(PROJECT_ROOT))
from watchers.base_watcher import BaseWatcher


# File types and their priority mapping
FILE_PRIORITY = {
    ".pdf": "HIGH",
    ".docx": "HIGH",
    ".doc": "HIGH",
    ".xlsx": "MEDIUM",
    ".csv": "MEDIUM",
    ".txt": "LOW",
    ".md": "LOW",
    ".png": "LOW",
    ".jpg": "LOW",
    ".jpeg": "LOW",
}


class InboxEventHandler(FileSystemEventHandler):
    """Handles file system events in the /Inbox folder."""

    def __init__(self, watcher: "FilesystemWatcher"):
        self.watcher = watcher
        self.processed = set()

    def on_created(self, event):
        if event.is_directory:
            return
        src = Path(event.src_path)
        if src.name.startswith(".") or src.name == ".gitkeep":
            return
        if str(src) not in self.processed:
            self.processed.add(str(src))
            self.watcher.create_action_file(src)
            self.watcher.logger.info(f"New file detected: {src.name}")


class FilesystemWatcher(BaseWatcher):
    """
    Watches /Inbox folder for new files.
    Creates structured action files in /Needs_Action.
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=5)
        self.observer = Observer()
        self.event_handler = InboxEventHandler(self)

    def check_for_updates(self) -> list:
        # Watchdog handles this via events — not used in polling mode
        return []

    def create_action_file(self, file_path: Path) -> Path:
        """Create a structured .md file in /Needs_Action for the dropped file."""
        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H-%M-%S")
        safe_name = file_path.stem.replace(" ", "_")

        suffix = file_path.suffix.lower()
        priority = FILE_PRIORITY.get(suffix, "MEDIUM")
        file_size = file_path.stat().st_size if file_path.exists() else 0

        # Copy file to Needs_Action for processing
        dest_file = self.needs_action / file_path.name
        if file_path.exists():
            shutil.copy2(file_path, dest_file)

        # Create metadata .md file
        md_filename = f"FILE_{date_str}_{time_str}_{safe_name}.md"
        md_path = self.needs_action / md_filename

        content = f"""---
type: file_drop
original_name: {file_path.name}
file_type: {suffix if suffix else "unknown"}
size_bytes: {file_size}
priority: {priority}
received: {timestamp.isoformat()}
status: pending
source: inbox
---

## File Received: {file_path.name}

**Received at**: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}
**File type**: `{suffix if suffix else "unknown"}`
**Size**: {file_size:,} bytes
**Priority**: {priority}

## Suggested Actions
- [ ] Review file contents
- [ ] Categorize and tag
- [ ] Take required action based on file type
- [ ] Move to /Done when complete

## Notes
_Add any processing notes here._
"""
        md_path.write_text(content)
        self.log_action("INBOX_FILE", f"`{file_path.name}` → created `{md_filename}`")
        return md_path

    def run(self):
        """Start the filesystem watcher using watchdog Observer."""
        self.logger.info(f"Starting FilesystemWatcher...")
        self.logger.info(f"Watching: {self.inbox}")

        self.observer.schedule(self.event_handler, str(self.inbox), recursive=False)
        self.observer.start()

        self.logger.info("Watcher active. Drop files into /Inbox to trigger processing.")
        self.logger.info("Press Ctrl+C to stop.")

        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            self.logger.info("Watcher stopped.")

        self.observer.join()


def main():
    parser = argparse.ArgumentParser(description="Filesystem Watcher for AI Employee")
    parser.add_argument(
        "--vault",
        default="AI_Employee_Vault",
        help="Path to Obsidian vault (default: AI_Employee_Vault)",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault)
    if not vault_path.is_absolute():
        vault_path = Path(__file__).parent.parent / vault_path

    watcher = FilesystemWatcher(str(vault_path))
    watcher.run()


if __name__ == "__main__":
    main()
