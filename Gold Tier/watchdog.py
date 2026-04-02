"""Process watchdog for Gold Tier runtime services."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from audit_logger import append_json_log


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    args: list[str]
    enabled: bool = True


class ProcessWatchdog:
    def __init__(self, project_root: Path, *, interval_seconds: int = 5) -> None:
        self.project_root = project_root.resolve()
        self.vault = self.project_root / "AI_Employee_Vault"
        self.logs = self.vault / "Logs"
        self.interval_seconds = interval_seconds
        self.processes: dict[str, subprocess.Popen[str]] = {}
        self.log_file = self.logs / f"{datetime.now().strftime('%Y-%m-%d')}_watchdog.log"
        self.logs.mkdir(parents=True, exist_ok=True)
        self._runner = self._base_runner()

    def _base_runner(self) -> list[str]:
        if shutil_which("uv"):
            return ["uv", "run", "python"]
        return [sys.executable]

    def _specs(self) -> list[ServiceSpec]:
        credentials_path = self.vault / "credentials.json"
        return [
            ServiceSpec("filesystem_watcher", ["watchers/filesystem_watcher.py", "--vault", "AI_Employee_Vault"]),
            ServiceSpec(
                "gmail_watcher",
                ["watchers/GmailWatcher.py", "--vault", "AI_Employee_Vault"],
                enabled=credentials_path.exists(),
            ),
            ServiceSpec("whatsapp_watcher", ["watchers/WhatsAppWatcher.py", "--vault", "AI_Employee_Vault"]),
            ServiceSpec("hitl_orchestrator", ["watchers/hitl_orchestrator.py", "--vault", "AI_Employee_Vault"]),
            ServiceSpec("skill_orchestrator", ["orchestrator.py", "--project-root", "."]),
            ServiceSpec("ralph_loop", ["ralph_loop.py", "--project-root", "."]),
        ]

    def _log(self, event_type: str, message: str, **payload: object) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{stamp}] {event_type}: {message}"
        print(line, flush=True)
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        append_json_log(
            self.logs,
            {
                "event_type": event_type,
                "message": message,
                **payload,
            },
        )

    def _start_service(self, spec: ServiceSpec) -> None:
        command = [*self._runner, *spec.args]
        process = subprocess.Popen(
            command,
            cwd=self.project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.processes[spec.name] = process
        self._log("watchdog_start", f"Started {spec.name}", command=command, pid=process.pid)

    def _stop_service(self, name: str, process: subprocess.Popen[str]) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self._log("watchdog_stop", f"Stopped {name}", pid=process.pid, returncode=process.returncode)

    def start_all(self) -> None:
        for spec in self._specs():
            if not spec.enabled:
                self._log("watchdog_skip", f"Skipped {spec.name}", reason="disabled by local prerequisites")
                continue
            self._start_service(spec)

    def monitor_forever(self) -> None:
        self.start_all()
        try:
            while True:
                time.sleep(self.interval_seconds)
                for spec in self._specs():
                    if not spec.enabled:
                        continue
                    process = self.processes.get(spec.name)
                    if process is None:
                        self._start_service(spec)
                        continue
                    returncode = process.poll()
                    if returncode is None:
                        continue
                    self._log(
                        "watchdog_restart",
                        f"Restarting {spec.name}",
                        pid=process.pid,
                        returncode=returncode,
                    )
                    self._start_service(spec)
        except KeyboardInterrupt:
            self._log("watchdog_shutdown", "Stopping all supervised services")
            for name, process in list(self.processes.items()):
                self._stop_service(name, process)


def shutil_which(name: str) -> str | None:
    for entry in os.getenv("PATH", "").split(os.pathsep):
        candidate = Path(entry) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Gold Tier process watchdog")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root path (default: current directory)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Process health check interval in seconds (default: 5)",
    )
    args = parser.parse_args()

    watchdog = ProcessWatchdog(Path(args.project_root), interval_seconds=args.interval)
    signal.signal(signal.SIGTERM, lambda *_args: sys.exit(0))
    watchdog.monitor_forever()


if __name__ == "__main__":
    main()
