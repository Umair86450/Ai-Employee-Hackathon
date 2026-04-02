"""Gold Tier Ralph Wiggum loop controller.

This wrapper drives Codex in small, auditable iterations for `Needs_Action`
tasks. It keeps workflow-critical state in Python while delegating reasoning
and content generation to Codex skills.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any


DEFAULT_INTERVAL_SECONDS = 30
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_CODEX_TIMEOUT = 1800
STATE_FILENAME = ".ralph_loop_state.json"


@dataclass(frozen=True)
class TaskSignals:
    requires_invoice: bool
    requires_payment: bool
    requires_email: bool
    social_platforms: tuple[str, ...]
    summary: str

    @property
    def requires_social(self) -> bool:
        return bool(self.social_platforms)


@dataclass(frozen=True)
class Snapshot:
    pending_approval: frozenset[str]
    approved: frozenset[str]
    rejected: frozenset[str]
    done: frozenset[str]


class RalphLoop:
    def __init__(
        self,
        *,
        project_root: Path,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        codex_bin: str = "codex",
        codex_timeout_seconds: int = DEFAULT_CODEX_TIMEOUT,
        max_attempts_per_task: int = DEFAULT_MAX_ATTEMPTS,
        task_file: str = "",
    ) -> None:
        self.project_root = project_root.resolve()
        self.vault = self.project_root / "AI_Employee_Vault"
        self.needs_action = self.vault / "Needs_Action"
        self.done = self.vault / "Done"
        self.pending_approval = self.vault / "Pending_Approval"
        self.approved = self.vault / "Approved"
        self.rejected = self.vault / "Rejected"
        self.logs = self.vault / "Logs"
        self.handbook = self.vault / "Company_Handbook.md"
        self.interval_seconds = interval_seconds
        self.codex_bin = codex_bin
        self.codex_timeout_seconds = codex_timeout_seconds
        self.max_attempts_per_task = max(1, max_attempts_per_task)
        self.task_file = task_file.strip()
        self.state_path = self.project_root / STATE_FILENAME
        self.state = self._load_state()

        for folder in [
            self.vault,
            self.needs_action,
            self.done,
            self.pending_approval,
            self.approved,
            self.rejected,
            self.logs,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    def _default_state(self) -> dict[str, Any]:
        return {"attempts_by_file": {}}

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._default_state()
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return self._default_state()
        state = self._default_state()
        state.update(raw)
        if not isinstance(state.get("attempts_by_file"), dict):
            state["attempts_by_file"] = {}
        return state

    def _save_state(self) -> None:
        self.state_path.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def _today_log(self) -> Path:
        return self.logs / f"{datetime.now().strftime('%Y-%m-%d')}.md"

    def _log(self, message: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"- `{stamp}` | **RALPH_LOOP** | {message}"
        print(line, flush=True)
        log_path = self._today_log()
        if not log_path.exists():
            log_path.write_text(f"# Log — {datetime.now().strftime('%Y-%m-%d')}\n", encoding="utf-8")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n" + line)

    def _needs_action_files(self) -> list[Path]:
        files = [
            path
            for path in self.needs_action.iterdir()
            if path.is_file() and path.name != ".gitkeep" and not path.name.startswith(".")
        ]
        files.sort(key=lambda item: item.name.lower())
        if not self.task_file:
            return files

        requested = Path(self.task_file)
        if not requested.is_absolute():
            requested = self.project_root / requested
        requested = requested.resolve()
        return [path for path in files if path.resolve() == requested]

    def _snapshot(self) -> Snapshot:
        def names(folder: Path) -> frozenset[str]:
            return frozenset(
                item.name
                for item in folder.iterdir()
                if item.is_file() and item.name != ".gitkeep" and not item.name.startswith(".")
            )

        return Snapshot(
            pending_approval=names(self.pending_approval),
            approved=names(self.approved),
            rejected=names(self.rejected),
            done=names(self.done),
        )

    def _read_task_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")

    def _strip_frontmatter(self, text: str) -> str:
        if not text.startswith("---\n"):
            return text
        end = text.find("\n---\n", 4)
        if end == -1:
            return text
        return text[end + len("\n---\n") :]

    def detect_task_signals(self, path: Path) -> TaskSignals:
        text = self._read_task_text(path)
        body = self._strip_frontmatter(text)
        lowered = body.lower()

        requires_invoice = any(
            token in lowered
            for token in [
                "invoice",
                "customer invoice",
                "create invoice",
                "bill the client",
                "bill customer",
                "odoo invoice",
            ]
        )
        requires_payment = any(
            token in lowered
            for token in [
                "post payment",
                "record payment",
                "receive payment",
                "customer payment",
                "vendor payment",
            ]
        )
        requires_email = any(
            token in lowered
            for token in [
                "send email",
                "email",
                "reply to",
                "follow up by email",
                "mail the client",
            ]
        )

        social_platforms: list[str] = []
        platform_keywords = {
            "facebook": ["facebook", "fb post", "post on facebook"],
            "instagram": ["instagram", "ig post", "post on instagram"],
            "twitter": ["twitter", "x post", "post on x", "tweet", "thread"],
            "linkedin": ["linkedin", "post on linkedin"],
        }
        for platform, keywords in platform_keywords.items():
            if any(keyword in lowered for keyword in keywords):
                social_platforms.append(platform)

        if not social_platforms and any(
            token in lowered
            for token in [
                "social post",
                "social media",
                "post this",
                "promote this",
                "publish a post",
            ]
        ):
            social_platforms.append("linkedin")

        summary = self._summarize_task(path.name, body)
        return TaskSignals(
            requires_invoice=requires_invoice,
            requires_payment=requires_payment,
            requires_email=requires_email,
            social_platforms=tuple(social_platforms),
            summary=summary,
        )

    def _summarize_task(self, fallback_name: str, text: str) -> str:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                return line.lstrip("#").strip()[:200]
            if line.startswith("- ") or line.startswith("* "):
                continue
            return line[:200]
        return fallback_name

    def _approval_action_types(self, signals: TaskSignals) -> list[str]:
        actions: list[str] = []
        if signals.requires_invoice:
            actions.append("odoo_create_invoice")
        if signals.requires_payment:
            actions.append("odoo_post_payment")
        if signals.requires_email:
            actions.append("email_send")
        for platform in signals.social_platforms:
            if platform == "facebook":
                actions.append("facebook_post")
            elif platform == "instagram":
                actions.append("instagram_post")
            elif platform == "twitter":
                actions.append("twitter_post")
            elif platform == "linkedin":
                actions.append("linkedin_post")
        return actions

    def _build_prompt(self, path: Path, signals: TaskSignals) -> str:
        rel_task = path.relative_to(self.project_root)
        rel_handbook = self.handbook.relative_to(self.project_root)
        action_types = self._approval_action_types(signals)
        action_list = ", ".join(action_types) if action_types else "none detected"
        social_targets = ", ".join(signals.social_platforms) if signals.social_platforms else "none"

        return dedent(
            f"""
            Follow the Ralph Wiggum loop policy in `AGENTS.md` for this one task only.

            Read `{rel_handbook}` before acting.
            Process exactly this source file: `{rel_task}`.

            Task summary:
            - {signals.summary}

            Detected actions to complete in this pass:
            - Odoo invoice: {"yes" if signals.requires_invoice else "no"}
            - Odoo payment: {"yes" if signals.requires_payment else "no"}
            - Email send/reply: {"yes" if signals.requires_email else "no"}
            - Social platforms: {social_targets}
            - Expected approval action types: {action_list}

            Execution rules:
            - Use existing repo workflows only: skills under `.agents/skills/`, `main.py --create-approval`, and existing MCP routing.
            - Never execute sensitive external actions directly. Create approval files in `AI_Employee_Vault/Pending_Approval/`.
            - For Odoo accounting actions, use `odoo_create_invoice` and `odoo_post_payment`.
            - For email actions, use `email_send`.
            - For social actions, use the explicit platform action type when available; if the task is generic social, use LinkedIn by default.
            - If the task requires multiple steps, complete all applicable steps in one pass before marking the task complete.
            - Validate what you created.
            - Append a concise result to today's log and refresh `AI_Employee_Vault/Dashboard.md`.

            Completion policy:
            - Use file-move completion, not deletion.
            - When the task reaches a terminal state, move the original source file out of `AI_Employee_Vault/Needs_Action/` into `AI_Employee_Vault/Done/`.
            - Terminal state includes:
              1. All non-sensitive work finished, or
              2. All required approval requests created, or
              3. Clean stop due to missing credentials, policy boundary, or repeated failure.
            - Do not leave the source file in `Needs_Action/` if you already created the required approvals and handoff is complete.
            - Do not modify unrelated files.
            """
        ).strip()

    def _run_codex(self, prompt: str) -> subprocess.CompletedProcess[str]:
        cmd = [
            self.codex_bin,
            "exec",
            "--full-auto",
            "--cd",
            str(self.project_root),
            prompt,
        ]
        codex_model = os.getenv("CODEX_MODEL", "").strip()
        if codex_model:
            cmd[2:2] = ["--model", codex_model]
        return subprocess.run(
            cmd,
            cwd=self.project_root,
            text=True,
            capture_output=True,
            timeout=self.codex_timeout_seconds,
        )

    def _move_to_done(self, source_file: Path, reason: str) -> Path:
        target = self.done / source_file.name
        if target.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = self.done / f"{source_file.stem}_{stamp}{source_file.suffix}"
        shutil.move(str(source_file), str(target))
        self._log(f"Moved `{target.name}` to Done ({reason}).")
        return target

    def _refresh_dashboard(self) -> None:
        main_py = self.project_root / "main.py"
        if not main_py.exists():
            return
        result = subprocess.run(
            [sys.executable, str(main_py), "--update-dash"],
            cwd=self.project_root,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            stderr_tail = (result.stderr or "").strip()[-800:]
            self._log(f"Dashboard refresh failed: {stderr_tail or 'unknown error'}")

    def _validate_outcome(self, source_file: Path, before: Snapshot) -> tuple[str, list[str]]:
        after = self._snapshot()
        new_pending = sorted(after.pending_approval - before.pending_approval)
        new_approved = sorted(after.approved - before.approved)
        new_rejected = sorted(after.rejected - before.rejected)
        new_done = sorted(after.done - before.done)

        if not source_file.exists():
            details = []
            if new_done:
                details.append(f"done={', '.join(new_done)}")
            return "completed", details

        new_approval_files = new_pending + new_approved + new_rejected
        if new_approval_files:
            self._move_to_done(source_file, "approval boundary reached")
            details = [f"approvals={', '.join(new_approval_files)}"]
            return "approval_boundary", details

        if new_done:
            self._move_to_done(source_file, "related completion artifact created")
            details = [f"done_artifacts={', '.join(new_done)}"]
            return "completed", details

        return "retry", []

    def process_task(self, source_file: Path) -> dict[str, Any]:
        source_file = source_file.resolve()
        signals = self.detect_task_signals(source_file)
        attempts = self.state.setdefault("attempts_by_file", {})
        key = source_file.name

        for attempt in range(1, self.max_attempts_per_task + 1):
            attempts[key] = attempt
            self._save_state()
            self._log(
                f"Iteration {attempt}/{self.max_attempts_per_task} for `{source_file.name}` "
                f"(invoice={signals.requires_invoice}, payment={signals.requires_payment}, "
                f"email={signals.requires_email}, social={list(signals.social_platforms)})"
            )

            before = self._snapshot()
            prompt = self._build_prompt(source_file, signals)
            result = self._run_codex(prompt)
            if result.returncode != 0:
                stderr_tail = (result.stderr or "").strip()[-1200:]
                stdout_tail = (result.stdout or "").strip()[-1200:]
                self._log(
                    f"Codex failed for `{source_file.name}` "
                    f"(exit={result.returncode}) stdout_tail={stdout_tail!r} stderr_tail={stderr_tail!r}"
                )
            status, details = self._validate_outcome(source_file, before)
            if status != "retry":
                attempts.pop(key, None)
                self._save_state()
                self._refresh_dashboard()
                self._log(
                    f"Terminal state for `{source_file.name}`: {status}"
                    + (f" ({'; '.join(details)})" if details else "")
                )
                return {
                    "status": status,
                    "task": source_file.name,
                    "details": details,
                }

            self._log(f"No terminal progress for `{source_file.name}` on iteration {attempt}.")

        self._log(
            f"Stopping `{source_file.name}` after {self.max_attempts_per_task} iterations "
            "without a terminal outcome."
        )
        self._refresh_dashboard()
        return {"status": "stopped", "task": source_file.name, "details": ["max_attempts_reached"]}

    def run_once(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        files = self._needs_action_files()
        if not files:
            self._log("No Needs_Action files found for Ralph loop.")
            return results
        for task_file in files:
            if not task_file.exists():
                continue
            results.append(self.process_task(task_file))
        return results

    def run(self) -> None:
        self._log(
            f"Ralph loop started. Watching Needs_Action every {self.interval_seconds}s."
        )
        while True:
            try:
                self.run_once()
            except Exception as exc:
                self._log(f"Cycle error: {exc}")
            time.sleep(self.interval_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gold Tier Ralph Wiggum loop controller")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root path (default: current directory)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Polling interval in seconds (default: {DEFAULT_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one pass over current Needs_Action files and exit",
    )
    parser.add_argument(
        "--task-file",
        default="",
        help="Optional specific task file path to process",
    )
    parser.add_argument(
        "--codex-bin",
        default=os.getenv("CODEX_BIN", "codex"),
        help="Codex executable name/path (default: codex or CODEX_BIN env)",
    )
    parser.add_argument(
        "--codex-timeout",
        type=int,
        default=int(os.getenv("CODEX_TIMEOUT_SECONDS", str(DEFAULT_CODEX_TIMEOUT))),
        help="Timeout in seconds per Codex run",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS,
        help=f"Max Ralph iterations per task (default: {DEFAULT_MAX_ATTEMPTS})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    loop = RalphLoop(
        project_root=Path(args.project_root),
        interval_seconds=args.interval,
        codex_bin=args.codex_bin,
        codex_timeout_seconds=args.codex_timeout,
        max_attempts_per_task=args.max_attempts,
        task_file=args.task_file,
    )
    if args.once:
        loop.run_once()
    else:
        loop.run()


if __name__ == "__main__":
    main()
