"""
AI Employee — Silver Tier Control Plane
=======================================
Entry point for the Personal AI Employee system.

Usage:
    uv run main.py                  # Start Silver services
    uv run main.py --status         # Show vault status
    uv run main.py --help           # Show help
"""

import argparse
import json
import threading
import time
from datetime import datetime
from pathlib import Path

VAULT_PATH = Path(__file__).parent / "AI_Employee_Vault"


def ensure_vault_folders():
    """Ensure Silver Tier folders exist for HITL workflow."""
    required = [
        "Inbox",
        "Needs_Action",
        "Done",
        "Plans",
        "Pending_Approval",
        "Approved",
        "Rejected",
        "Logs",
    ]
    for name in required:
        (VAULT_PATH / name).mkdir(parents=True, exist_ok=True)


def show_status():
    """Print current vault status to terminal."""
    inbox = VAULT_PATH / "Inbox"
    needs_action = VAULT_PATH / "Needs_Action"
    done = VAULT_PATH / "Done"
    logs = VAULT_PATH / "Logs"
    plans = VAULT_PATH / "Plans"
    pending_approval = VAULT_PATH / "Pending_Approval"
    approved = VAULT_PATH / "Approved"
    rejected = VAULT_PATH / "Rejected"

    def count_files(folder: Path) -> int:
        return len([f for f in folder.iterdir() if f.is_file() and f.name != ".gitkeep"])

    print("\n" + "=" * 50)
    print("  AI Employee — Silver Tier — Status")
    print("=" * 50)
    print(f"  Vault     : {VAULT_PATH}")
    print(f"  Inbox     : {count_files(inbox)} files")
    print(f"  Needs Action: {count_files(needs_action)} files")
    print(f"  Done      : {count_files(done)} files")
    print(f"  Plans     : {count_files(plans)} files")
    print(f"  Pending Approval: {count_files(pending_approval)} files")
    print(f"  Approved  : {count_files(approved)} files")
    print(f"  Rejected  : {count_files(rejected)} files")
    print(f"  Logs      : {count_files(logs)} files")
    print("=" * 50 + "\n")


def update_dashboard():
    """Update Dashboard.md with current vault stats."""
    inbox = VAULT_PATH / "Inbox"
    needs_action = VAULT_PATH / "Needs_Action"
    done = VAULT_PATH / "Done"
    plans = VAULT_PATH / "Plans"
    pending_approval = VAULT_PATH / "Pending_Approval"
    approved = VAULT_PATH / "Approved"
    rejected = VAULT_PATH / "Rejected"
    logs = VAULT_PATH / "Logs"

    def count_files(folder: Path) -> int:
        return len([f for f in folder.iterdir() if f.is_file() and f.name != ".gitkeep"])

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dashboard = VAULT_PATH / "Dashboard.md"
    log_entries: list[str] = []
    today_log = logs / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    if today_log.exists():
        log_entries = [line.strip() for line in today_log.read_text(encoding="utf-8").splitlines() if line.strip().startswith("- ")][-5:]

    attention_items: list[str] = []
    if count_files(pending_approval):
        attention_items.append(f"- {count_files(pending_approval)} approval request(s) waiting for human review")
    if count_files(needs_action) > 0:
        attention_items.append(f"- {count_files(needs_action)} item(s) still pending in /Needs_Action")
    if not attention_items:
        attention_items.append("- No immediate owner action required")

    recent_activity = "\n".join(log_entries) if log_entries else "- No activity logged yet today"

    content = f"""# AI Employee Dashboard
---
last_updated: {now}
status: active
---

## System Status
| Component | Status |
|-----------|--------|
| Filesystem Watcher | Available |
| Gmail Watcher | Available |
| WhatsApp Watcher | Available |
| Skill Orchestrator | Available |
| HITL Orchestrator | Available |
| Vault Read/Write | Active |
| Agent Skills | Loaded |

## Inbox Summary
- **Inbox**: {count_files(inbox)} files waiting
- **Needs Action**: {count_files(needs_action)} files
- **Completed**: {count_files(done)} files total
- **Plans**: {count_files(plans)} files
- **Pending Approval**: {count_files(pending_approval)} files
- **Approved Queue**: {count_files(approved)} files
- **Rejected Queue**: {count_files(rejected)} files

## Quick Stats
| Folder | Count |
|--------|-------|
| /Inbox | {count_files(inbox)} |
| /Needs_Action | {count_files(needs_action)} |
| /Done | {count_files(done)} |
| /Plans | {count_files(plans)} |
| /Pending_Approval | {count_files(pending_approval)} |
| /Approved | {count_files(approved)} |
| /Rejected | {count_files(rejected)} |

## Owner Attention
{chr(10).join(attention_items)}

## Recent Activity
{recent_activity}

---
*Updated by AI Employee — {now}*
"""
    dashboard.write_text(content)
    print(f"Dashboard updated at {now}")


def start_filesystem_watcher():
    """Start the filesystem watcher."""
    from watchers.filesystem_watcher import FilesystemWatcher

    watcher = FilesystemWatcher(str(VAULT_PATH))
    watcher.run()


def start_gmail_watcher():
    """Start the Gmail watcher when credentials are available."""
    credentials_path = VAULT_PATH / "credentials.json"
    if not credentials_path.exists():
        print("Skipping Gmail watcher: credentials.json not found.")
        return

    from watchers.GmailWatcher import GmailWatcher

    watcher = GmailWatcher(str(VAULT_PATH))
    watcher.run()


def start_whatsapp_watcher():
    """Start the WhatsApp watcher."""
    from watchers.WhatsAppWatcher import WhatsAppWatcher

    watcher = WhatsAppWatcher(str(VAULT_PATH))
    watcher.run()


def start_hitl_orchestrator():
    """Start HITL orchestrator for approved actions."""
    from watchers.hitl_orchestrator import HITLOrchestrator

    orchestrator = HITLOrchestrator(str(VAULT_PATH))
    orchestrator.run()


def start_skill_orchestrator():
    """Start skill-driven Silver orchestrator."""
    from orchestrator import SilverOrchestrator

    orchestrator = SilverOrchestrator(project_root=Path(__file__).parent)
    orchestrator.run()


def _service_runner(label: str, target) -> None:
    try:
        print(f"Starting {label}...")
        target()
    except Exception as exc:
        print(f"{label} stopped: {exc}")


def start_services(
    *,
    enable_filesystem: bool = True,
    enable_gmail: bool = True,
    enable_whatsapp: bool = True,
    enable_hitl: bool = True,
    enable_skill_loop: bool = True,
):
    """Start Silver Tier services together."""
    services = []
    if enable_filesystem:
        services.append(("Filesystem Watcher", start_filesystem_watcher))
    if enable_gmail:
        services.append(("Gmail Watcher", start_gmail_watcher))
    if enable_whatsapp:
        services.append(("WhatsApp Watcher", start_whatsapp_watcher))
    if enable_hitl:
        services.append(("HITL Orchestrator", start_hitl_orchestrator))
    if enable_skill_loop:
        services.append(("Skill Orchestrator", start_skill_orchestrator))

    threads = [
        threading.Thread(target=_service_runner, args=(label, target), daemon=True)
        for label, target in services
    ]

    for thread in threads:
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")


def create_approval_request(
    *,
    action_type: str,
    objective: str,
    details: str,
    mcp_args: str,
    source_file: str,
    mcp_server: str,
    mcp_tool: str,
):
    """Create APPROVAL_*.md in /Pending_Approval for sensitive actions."""
    from watchers.hitl_orchestrator import HITLOrchestrator

    try:
        parsed_args = json.loads(mcp_args) if mcp_args else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"--mcp-args must be valid JSON: {exc}") from exc

    orchestrator = HITLOrchestrator(str(VAULT_PATH))
    path = orchestrator.create_approval_request(
        action_type=action_type,
        objective=objective,
        details=details,
        mcp_arguments=parsed_args,
        source_file=source_file,
        mcp_server=mcp_server,
        mcp_tool=mcp_tool,
    )
    print(f"Approval file created: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="AI Employee — Silver Tier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  (no args)       Start Silver services
  --status        Show vault status
  --update-dash   Update Dashboard.md
  --run-hitl      Start HITL orchestrator only
  --run-orchestrator Start skill orchestrator only
  --create-approval --action-type ... --objective ... --details ... [--mcp-args JSON]
        """,
    )
    parser.add_argument("--status", action="store_true", help="Show vault status")
    parser.add_argument("--update-dash", action="store_true", help="Update Dashboard.md")
    parser.add_argument("--run-hitl", action="store_true", help="Run HITL orchestrator only")
    parser.add_argument("--run-orchestrator", action="store_true", help="Run Silver skill orchestrator only")
    parser.add_argument("--no-filesystem", action="store_true", help="Do not start filesystem watcher")
    parser.add_argument("--no-gmail", action="store_true", help="Do not start Gmail watcher")
    parser.add_argument("--no-whatsapp", action="store_true", help="Do not start WhatsApp watcher")
    parser.add_argument("--no-hitl", action="store_true", help="Do not start HITL orchestrator")
    parser.add_argument("--no-skill-loop", action="store_true", help="Do not start Silver skill loop")
    parser.add_argument(
        "--create-approval",
        action="store_true",
        help="Create APPROVAL_*.md request in /Pending_Approval",
    )
    parser.add_argument(
        "--action-type",
        default="",
        help="Sensitive action type: email_send | linkedin_post | payment",
    )
    parser.add_argument("--objective", default="", help="Short objective for approval")
    parser.add_argument("--details", default="", help="Details for approver review")
    parser.add_argument(
        "--mcp-args",
        default="{}",
        help='MCP tool args JSON string, e.g. \'{"to":"a@b.com","subject":"Hi","body":"..."}\'',
    )
    parser.add_argument("--source-file", default="", help="Optional source task file path")
    parser.add_argument("--mcp-server", default="", help="Optional MCP server override")
    parser.add_argument("--mcp-tool", default="", help="Optional MCP tool override")

    args = parser.parse_args()
    ensure_vault_folders()

    if args.status:
        show_status()
    elif args.update_dash:
        update_dashboard()
    elif args.run_hitl:
        print("Starting Silver Tier HITL Orchestrator...")
        start_hitl_orchestrator()
    elif args.run_orchestrator:
        print("Starting Silver Tier Skill Orchestrator...")
        start_skill_orchestrator()
    elif args.create_approval:
        if not args.action_type or not args.objective or not args.details:
            parser.error("--create-approval requires --action-type, --objective, and --details")
        create_approval_request(
            action_type=args.action_type,
            objective=args.objective,
            details=args.details,
            mcp_args=args.mcp_args,
            source_file=args.source_file,
            mcp_server=args.mcp_server,
            mcp_tool=args.mcp_tool,
        )
    else:
        print("Starting AI Employee Silver services...")
        start_services(
            enable_filesystem=not args.no_filesystem,
            enable_gmail=not args.no_gmail,
            enable_whatsapp=not args.no_whatsapp,
            enable_hitl=not args.no_hitl,
            enable_skill_loop=not args.no_skill_loop,
        )


if __name__ == "__main__":
    main()
