"""
Silver Tier end-to-end test script.

Flow:
1) Drop dummy Gmail + WhatsApp files into /Needs_Action.
2) Run orchestrator full flow (skills-driven).
3) Move one approval file from /Pending_Approval -> /Approved.
4) Run orchestrator again to process Approved HITL.
5) Print Dashboard + latest Plan + latest approval file.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VAULT = PROJECT_ROOT / "AI_Employee_Vault"
NEEDS_ACTION = VAULT / "Needs_Action"
PLANS = VAULT / "Plans"
PENDING_APPROVAL = VAULT / "Pending_Approval"
APPROVED = VAULT / "Approved"
DASHBOARD = VAULT / "Dashboard.md"


def _ensure_dirs() -> None:
    for folder in [NEEDS_ACTION, PLANS, PENDING_APPROVAL, APPROVED]:
        folder.mkdir(parents=True, exist_ok=True)


def _write_dummy_inputs() -> tuple[Path, Path]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    gmail = NEEDS_ACTION / f"EMAIL_TEST_{ts}.md"
    whatsapp = NEEDS_ACTION / f"WHATSAPP_TEST_{ts}.md"

    gmail.write_text(
        f"""---
type: email
id: TEST-{ts}
from: "demo.sender@example.com"
subject: "Client follow-up: AI employee pricing"
received: "{datetime.now().isoformat()}"
priority: HIGH
status: pending
---

Client is asking for pricing and onboarding timeline.
Please prepare response plan and include any required approvals.
""",
        encoding="utf-8",
    )

    whatsapp.write_text(
        f"""---
type: whatsapp
chat: "Pak Angels AI Group"
sender: "+92-300-0000000"
received: "{datetime.now().isoformat()}"
priority: MEDIUM
status: pending
---

Need a concise post explaining why Digital AI Employee can run 24/7 compared to 8-hour human shift.
Also ask for next-step CTA.
""",
        encoding="utf-8",
    )

    return gmail, whatsapp


def _run_orchestrator_once(*, force_linkedin: bool) -> None:
    cmd = [
        "python3",
        "orchestrator.py",
        "--project-root",
        str(PROJECT_ROOT),
        "--once",
    ]
    if force_linkedin:
        cmd.append("--force-linkedin")
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def _latest_file(folder: Path, pattern: str) -> Path | None:
    matches = list(folder.glob(pattern))
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def _approve_one_pending_file() -> Path | None:
    candidate = _latest_file(PENDING_APPROVAL, "APPROVAL_*.md")
    if candidate is None:
        return None
    destination = APPROVED / candidate.name
    if destination.exists():
        destination = APPROVED / f"{candidate.stem}_{datetime.now().strftime('%H%M%S')}.md"
    shutil.move(str(candidate), str(destination))
    return destination


def _print_file(title: str, path: Path | None) -> None:
    print(f"\n===== {title} =====")
    if path is None or not path.exists():
        print("(not found)")
        return
    print(f"Path: {path}")
    print(path.read_text(encoding="utf-8"))


def main() -> None:
    _ensure_dirs()
    gmail, whatsapp = _write_dummy_inputs()
    print("Created dummy files:")
    print(f"- {gmail}")
    print(f"- {whatsapp}")

    # First run: should detect Needs_Action files and trigger skills.
    _run_orchestrator_once(force_linkedin=True)

    # Move one approval to Approved and run again for HITL processing.
    approved_file = _approve_one_pending_file()
    if approved_file:
        print(f"Moved for approval processing: {approved_file}")
        _run_orchestrator_once(force_linkedin=False)
    else:
        print("No pending approval file found to move into /Approved.")

    latest_plan = _latest_file(PLANS, "PLAN_*.md")
    latest_approval = _latest_file(APPROVED, "APPROVAL_*.md") or _latest_file(
        PENDING_APPROVAL, "APPROVAL_*.md"
    )

    _print_file("Dashboard.md", DASHBOARD)
    _print_file("Latest Plan", latest_plan)
    _print_file("Latest Approval File", latest_approval)


if __name__ == "__main__":
    main()
