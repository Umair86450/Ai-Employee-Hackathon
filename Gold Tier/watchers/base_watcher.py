"""
Base Watcher - Template for all watcher scripts.
All watchers inherit from this class.
"""

import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class BaseWatcher(ABC):
    def __init__(self, vault_path: str, check_interval: int = 30):
        self.vault_path = Path(vault_path)
        self.inbox = self.vault_path / "Inbox"
        self.needs_action = self.vault_path / "Needs_Action"
        self.done = self.vault_path / "Done"
        self.logs = self.vault_path / "Logs"
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)

        # Ensure required folders exist
        for folder in [self.inbox, self.needs_action, self.done, self.logs]:
            folder.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def check_for_updates(self) -> list:
        """Return list of new items to process."""
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Create .md file in Needs_Action folder."""
        pass

    def log_action(self, action_type: str, details: str):
        """Write a log entry to today's log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs / f"{today}.md"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n- `{timestamp}` | **{action_type}** | {details}"

        if not log_file.exists():
            log_file.write_text(f"# Log — {today}\n")

        with open(log_file, "a") as f:
            f.write(entry)

    def run(self):
        self.logger.info(f"Starting {self.__class__.__name__}...")
        self.logger.info(f"Vault: {self.vault_path}")
        self.logger.info(f"Check interval: {self.check_interval}s")

        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    path = self.create_action_file(item)
                    self.logger.info(f"Created action file: {path.name}")
                    self.log_action("FILE_DETECTED", f"Created {path.name}")
            except KeyboardInterrupt:
                self.logger.info("Stopping watcher...")
                break
            except Exception as e:
                self.logger.error(f"Error: {e}")
            time.sleep(self.check_interval)
