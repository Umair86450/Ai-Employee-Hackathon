"""Gold Tier orchestrator.

Responsibilities:
- Coordinate personal-domain intake from Gmail/WhatsApp via `Needs_Action`
- Route business-domain execution across Odoo, email, and social approval flows
- Run Ralph loop passes for multi-step autonomous work
- Process approved HITL actions
- Generate recurring social drafts across LinkedIn, Facebook, Instagram, and X
- Generate the weekly CEO accounting audit/briefing
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillRef:
    rel_path: str
    label: str


SKILL_CREATE_PLAN = SkillRef(
    rel_path=".agents/skills/create-plan/SKILL_create_plan.md",
    label="create-plan",
)
SKILL_PROCESS_TASK = SkillRef(
    rel_path=".agents/skills/process-task/SKILL_process_task.md",
    label="process-task",
)
SKILL_PROCESS_APPROVED = SkillRef(
    rel_path=".agents/skills/process-approved/SKILL_process_approved.md",
    label="process-approved",
)
SKILL_UPDATE_DASHBOARD = SkillRef(
    rel_path=".agents/skills/update-dashboard/SKILL_update_dashboard.md",
    label="update-dashboard",
)
SKILL_POST_LINKEDIN = SkillRef(
    rel_path=".agents/skills/post-linkedin/SKILL.md",
    label="post-linkedin",
)
SKILL_POST_FACEBOOK = SkillRef(
    rel_path=".agents/skills/post-facebook/SKILL.md",
    label="post-facebook",
)
SKILL_POST_INSTAGRAM = SkillRef(
    rel_path=".agents/skills/post-instagram/SKILL.md",
    label="post-instagram",
)
SKILL_POST_TWITTER = SkillRef(
    rel_path=".agents/skills/post-twitter/SKILL.md",
    label="post-twitter",
)
SKILL_WEEKLY_CEO_BRIEFING = SkillRef(
    rel_path=".agents/skills/weekly-ceo-briefing/SKILL.md",
    label="weekly-ceo-briefing",
)


class GoldOrchestrator:
    def __init__(
        self,
        *,
        project_root: Path,
        interval_seconds: int = 15,
        codex_bin: str = "codex",
        codex_timeout_seconds: int = 1200,
        force_linkedin: bool = False,
        force_twitter: bool = False,
        force_weekly_audit: bool = False,
        enable_ralph_loop: bool = True,
    ) -> None:
        self.project_root = project_root.resolve()
        self.vault = self.project_root / "AI_Employee_Vault"
        self.needs_action = self.vault / "Needs_Action"
        self.approved = self.vault / "Approved"
        self.logs = self.vault / "Logs"
        self.state_path = self.project_root / ".gold_orchestrator_state.json"
        self.interval_seconds = interval_seconds
        self.codex_bin = codex_bin
        self.codex_timeout_seconds = codex_timeout_seconds
        self.force_linkedin = force_linkedin
        self.force_twitter = force_twitter
        self.force_weekly_audit = force_weekly_audit
        self.enable_ralph_loop = enable_ralph_loop
        self.state = self._load_state()

        for folder in [self.vault, self.needs_action, self.approved, self.logs]:
            folder.mkdir(parents=True, exist_ok=True)

    def _log(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line, flush=True)
        log_file = self.logs / f"{datetime.now().strftime('%Y-%m-%d')}_orchestrator.log"
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _default_state(self) -> dict[str, Any]:
        return {
            "processed_needs_action_signatures": [],
            "last_linkedin_date": "",
            "last_facebook_week": "",
            "last_instagram_week": "",
            "last_twitter_week": "",
            "last_ceo_briefing_week": "",
        }

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._default_state()
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            state = self._default_state()
            state.update(raw)
            if not isinstance(state.get("processed_needs_action_signatures"), list):
                state["processed_needs_action_signatures"] = []
            return state
        except Exception:
            return self._default_state()

    def _save_state(self) -> None:
        processed = self.state.get("processed_needs_action_signatures", [])
        if len(processed) > 5000:
            self.state["processed_needs_action_signatures"] = processed[-5000:]
        self.state_path.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def _file_sig(self, path: Path) -> str:
        stat = path.stat()
        return f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}"

    def _needs_action_files(self) -> list[Path]:
        return sorted(
            [
                p
                for p in self.needs_action.iterdir()
                if p.is_file() and p.name != ".gitkeep" and not p.name.startswith(".")
            ],
            key=lambda p: p.name.lower(),
        )

    def _approved_files(self) -> list[Path]:
        return sorted(
            [
                p
                for p in self.approved.iterdir()
                if p.is_file() and p.name.startswith("APPROVAL_") and p.suffix.lower() == ".md"
            ],
            key=lambda p: p.name.lower(),
        )

    def _bootstrap_plan_for(self, source_file: Path) -> Path:
        plans_dir = self.vault / "Plans"
        plans_dir.mkdir(parents=True, exist_ok=True)

        plan_path = plans_dir / f"PLAN_{source_file.stem}.md"
        if plan_path.exists():
            return plan_path

        try:
            snippet = source_file.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            snippet = ""

        objective = snippet.splitlines()[-1].strip() if snippet else f"Review {source_file.name}"
        objective = objective[:240] if objective else f"Review {source_file.name}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content = f"""# PLAN_{source_file.stem}

Source File: {source_file.name}
Created At: {created_at}

## Objective
{objective}

## Steps
- [ ] Review the source file and confirm business intent
- [ ] Decide whether external action or approval is required
- [ ] Complete processing and update dashboard/logs

## Suggested Actions
- Summarize the request and identify the next action
- Create approval request if the task is sensitive
- Move completed work out of /Needs_Action after processing

## Approval needed? TBD
- Reason: Awaiting skill-driven review of the source file
"""
        plan_path.write_text(content, encoding="utf-8")
        self._log(f"Bootstrapped plan file `{plan_path.name}` for `{source_file.name}`")
        return plan_path

    def _run_skill(self, skill: SkillRef, task: str) -> None:
        skill_abs = self.project_root / skill.rel_path
        if not skill_abs.exists():
            raise FileNotFoundError(f"Skill file not found: {skill_abs}")

        prompt = (
            f"Use skill file `{skill.rel_path}` and follow it exactly.\n"
            f"Task:\n{task}\n"
            "Constraints:\n"
            "- Execute via the skill workflow only.\n"
            "- Keep output concise.\n"
        )

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

        self._log(f"Running skill `{skill.label}`")
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            text=True,
            capture_output=True,
            timeout=self.codex_timeout_seconds,
        )
        if result.returncode != 0:
            stderr_tail = (result.stderr or "").strip()[-1200:]
            stdout_tail = (result.stdout or "").strip()[-1200:]
            raise RuntimeError(
                f"Skill `{skill.label}` failed (exit={result.returncode}). "
                f"stdout_tail={stdout_tail!r} stderr_tail={stderr_tail!r}"
            )

    def _run_ralph_loop_for_files(self, files: list[Path]) -> None:
        if not files:
            return

        from ralph_loop import RalphLoop

        loop = RalphLoop(
            project_root=self.project_root,
            interval_seconds=self.interval_seconds,
            codex_bin=self.codex_bin,
            codex_timeout_seconds=self.codex_timeout_seconds,
        )
        for path in files:
            if path.exists():
                self._log(f"Running Ralph loop for `{path.name}`")
                loop.process_task(path)

    def _handle_needs_action(self) -> None:
        files = self._needs_action_files()
        if not files:
            return

        processed = set(self.state.get("processed_needs_action_signatures", []))
        new_files = [p for p in files if self._file_sig(p) not in processed]
        if not new_files:
            return

        names = ", ".join(p.name for p in new_files)
        self._log(f"Detected new Needs_Action files: {names}")

        for path in new_files:
            self._bootstrap_plan_for(path)

        if self.enable_ralph_loop:
            self._run_ralph_loop_for_files(new_files)

        remaining = [path for path in new_files if path.exists()]
        if remaining:
            names_after_ralph = ", ".join(path.name for path in remaining)
            self._log(f"Fallback skill processing for remaining tasks: {names_after_ralph}")
            self._run_skill(
                SKILL_CREATE_PLAN,
                (
                    "Process all current files in AI_Employee_Vault/Needs_Action, create "
                    "PLAN_<timestamp>.md entries, and continue per skill instructions."
                ),
            )
            self._run_skill(
                SKILL_PROCESS_TASK,
                (
                    "Execute task processing workflow for current AI_Employee_Vault/Needs_Action "
                    "files, respecting sensitive-action approval rules."
                ),
            )
        self._run_skill(
            SKILL_UPDATE_DASHBOARD,
            "Refresh dashboard and logs after task processing.",
        )

        for p in new_files:
            if not p.exists():
                processed.add(self._file_sig_placeholder(p))
        self.state["processed_needs_action_signatures"] = sorted(processed)
        self._save_state()

    def _file_sig_placeholder(self, path: Path) -> str:
        return f"{path.name}:completed"

    def _handle_hitl_approved(self) -> None:
        approved_files = self._approved_files()
        if not approved_files:
            return

        names = ", ".join(p.name for p in approved_files)
        self._log(f"Approved queue detected: {names}")
        self._run_skill(
            SKILL_PROCESS_APPROVED,
            (
                "Process all APPROVAL_*.md files currently in AI_Employee_Vault/Approved. "
                "Execute approved MCP actions and preserve audit trail."
            ),
        )
        self._run_skill(
            SKILL_UPDATE_DASHBOARD,
            "Refresh dashboard and logs after approved-action processing.",
        )

    def _handle_daily_linkedin(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        last_run = str(self.state.get("last_linkedin_date", ""))
        if not self.force_linkedin and last_run == today:
            return

        self._log("Running daily LinkedIn skill")
        self._run_skill(
            SKILL_POST_LINKEDIN,
            (
                "Run daily LinkedIn workflow. Create a professional sales-focused post draft, "
                "generate image prompt, and create approval request only. Do not publish."
            ),
        )
        self.state["last_linkedin_date"] = today
        self._save_state()

    def _current_week_key(self) -> str:
        return datetime.now().strftime("%G-W%V")

    def _handle_weekly_social(self) -> None:
        week_key = self._current_week_key()

        if str(self.state.get("last_facebook_week", "")) != week_key:
            self._log("Running weekly Facebook skill")
            self._run_skill(
                SKILL_POST_FACEBOOK,
                (
                    "Run weekly Facebook workflow. Generate a business post from "
                    "AI_Employee_Vault/Business_Goals.md, create approval request only, "
                    "and use draft mode. Do not publish."
                ),
            )
            self.state["last_facebook_week"] = week_key

        if str(self.state.get("last_instagram_week", "")) != week_key:
            self._log("Running weekly Instagram skill")
            self._run_skill(
                SKILL_POST_INSTAGRAM,
                (
                    "Run weekly Instagram workflow. Generate a business caption from "
                    "AI_Employee_Vault/Business_Goals.md, create approval request only, "
                    "and use draft mode. Do not publish."
                ),
            )
            self.state["last_instagram_week"] = week_key

        if self.force_twitter or str(self.state.get("last_twitter_week", "")) != week_key:
            self._log("Running weekly X skill")
            self._run_skill(
                SKILL_POST_TWITTER,
                (
                    "Run weekly X workflow. Generate a business post or short thread from "
                    "recent Gold Tier activity, use draft mode unless explicit approval exists, "
                    "update Social_Summary/X_Summary.md, and create approval request only when needed."
                ),
            )
            self.state["last_twitter_week"] = week_key

        self._save_state()

    def _in_weekly_audit_window(self) -> bool:
        now = datetime.now()
        return now.weekday() == 4 and now.hour >= 22

    def _handle_weekly_ceo_briefing(self) -> None:
        week_key = self._current_week_key()
        if not self.force_weekly_audit and not self._in_weekly_audit_window():
            return
        if not self.force_weekly_audit and str(self.state.get("last_ceo_briefing_week", "")) == week_key:
            return

        self._log("Running weekly CEO briefing skill")
        self._run_skill(
            SKILL_WEEKLY_CEO_BRIEFING,
            (
                "Generate the weekly CEO briefing now using Odoo accounting, completed work, "
                "pending approvals, and recent logs. Save it into AI_Employee_Vault/Briefings/ "
                "and update dashboard/logs."
            ),
        )
        self.state["last_ceo_briefing_week"] = week_key
        self._save_state()

    def run_once(self) -> None:
        self._handle_needs_action()
        self._handle_hitl_approved()
        self._handle_daily_linkedin()
        self._handle_weekly_social()
        self._handle_weekly_ceo_briefing()

    def run(self) -> None:
        self._log(
            f"GoldOrchestrator started. Watching personal/business domains every {self.interval_seconds}s."
        )
        while True:
            try:
                self.run_once()
            except Exception as exc:
                self._log(f"Cycle error: {exc}")
            time.sleep(self.interval_seconds)


SilverOrchestrator = GoldOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gold Tier orchestrator")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root path (default: current directory)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Polling interval in seconds for watch loop (default: 15)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and exit",
    )
    parser.add_argument(
        "--force-linkedin",
        action="store_true",
        help="Force LinkedIn skill execution even if already run today",
    )
    parser.add_argument(
        "--force-twitter",
        action="store_true",
        help="Force X/Twitter skill execution even if already run this week",
    )
    parser.add_argument(
        "--force-weekly-audit",
        action="store_true",
        help="Force weekly CEO briefing even outside the Friday audit window",
    )
    parser.add_argument(
        "--disable-ralph-loop",
        action="store_true",
        help="Disable Ralph loop and use skill fallback only",
    )
    parser.add_argument(
        "--codex-bin",
        default=os.getenv("CODEX_BIN", "codex"),
        help="Codex executable name/path (default: codex or CODEX_BIN env)",
    )
    parser.add_argument(
        "--codex-timeout",
        type=int,
        default=int(os.getenv("CODEX_TIMEOUT_SECONDS", "1200")),
        help="Timeout in seconds per codex skill run (default: 1200)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    orchestrator = GoldOrchestrator(
        project_root=Path(args.project_root),
        interval_seconds=args.interval,
        codex_bin=args.codex_bin,
        codex_timeout_seconds=args.codex_timeout,
        force_linkedin=args.force_linkedin,
        force_twitter=args.force_twitter,
        force_weekly_audit=args.force_weekly_audit,
        enable_ralph_loop=not args.disable_ralph_loop,
    )
    if args.once:
        orchestrator.run_once()
    else:
        orchestrator.run()


if __name__ == "__main__":
    main()
