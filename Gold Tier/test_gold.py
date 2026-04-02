from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import ModuleType


fake_mcp = ModuleType("mcp")
fake_mcp.ClientSession = object
fake_mcp_client = ModuleType("mcp.client")
fake_mcp_stdio = ModuleType("mcp.client.stdio")
fake_mcp_stdio.StdioServerParameters = object
fake_mcp_stdio.stdio_client = object
sys.modules.setdefault("mcp", fake_mcp)
sys.modules.setdefault("mcp.client", fake_mcp_client)
sys.modules.setdefault("mcp.client.stdio", fake_mcp_stdio)

fake_watchdog = ModuleType("watchdog")
fake_watchdog_events = ModuleType("watchdog.events")
fake_watchdog_events.FileSystemEvent = object
fake_watchdog_events.FileSystemEventHandler = object
fake_watchdog_events.FileSystemMovedEvent = object
fake_watchdog_observers = ModuleType("watchdog.observers")
fake_watchdog_observers.Observer = object
sys.modules.setdefault("watchdog", fake_watchdog)
sys.modules.setdefault("watchdog.events", fake_watchdog_events)
sys.modules.setdefault("watchdog.observers", fake_watchdog_observers)

from orchestrator import GoldOrchestrator, SKILL_WEEKLY_CEO_BRIEFING
from ralph_loop import RalphLoop
from watchers.hitl_orchestrator import HITLOrchestrator


class GoldTierFlowTest(unittest.TestCase):
    def _make_project(self, tmpdir: str) -> Path:
        root = Path(tmpdir)
        vault = root / "AI_Employee_Vault"
        for name in [
            "Inbox",
            "Needs_Action",
            "Done",
            "Plans",
            "Pending_Approval",
            "Approved",
            "Queued",
            "Rejected",
            "Briefings",
            "Logs",
        ]:
            (vault / name).mkdir(parents=True, exist_ok=True)

        (vault / "Company_Handbook.md").write_text("# Handbook\n", encoding="utf-8")
        (vault / "Business_Goals.md").write_text(
            "# Goals\n- Close invoice-driven customer work\n- Maintain weekly social presence\n",
            encoding="utf-8",
        )
        (vault / "Dashboard.md").write_text("# Dashboard\n", encoding="utf-8")
        (root / "mcp.json").write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "odoo_mcp": {"command": "python", "args": ["fake_odoo.py"]},
                        "browser_mcp": {"command": "python", "args": ["fake_browser.py"]},
                        "email_mcp": {"command": "python", "args": ["fake_email.py"]},
                    }
                }
            ),
            encoding="utf-8",
        )
        return root

    def test_full_gold_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._make_project(tmpdir)
            vault = root / "AI_Employee_Vault"
            needs_action = vault / "Needs_Action"
            pending = vault / "Pending_Approval"
            approved = vault / "Approved"
            briefings = vault / "Briefings"

            task = needs_action / "WHATSAPP_invoice_request.md"
            task.write_text(
                (
                    "# WhatsApp request\n"
                    "Customer asked for an invoice in Odoo, email the invoice, and publish a short X update.\n"
                ),
                encoding="utf-8",
            )

            loop = RalphLoop(project_root=root, max_attempts_per_task=1)

            def fake_codex(_prompt: str):
                hitl = HITLOrchestrator(str(vault))
                hitl.create_approval_request(
                    action_type="odoo_create_invoice",
                    objective="Create customer invoice",
                    details="Create an invoice for the WhatsApp customer request",
                    mcp_arguments={"customer_name": "ABC Traders", "line_items": [{"product_name": "AI Employee Subscription", "quantity": 1, "price_unit": 50000}]},
                    source_file=task.name,
                )
                hitl.create_approval_request(
                    action_type="email_send",
                    objective="Email invoice to customer",
                    details="Send invoice confirmation after Odoo invoice creation",
                    mcp_arguments={"to": "client@example.com", "subject": "Your invoice", "body": "Invoice created."},
                    source_file=task.name,
                )
                hitl.create_approval_request(
                    action_type="twitter_post",
                    objective="Create X update",
                    details="Post a short approved update after invoice generation",
                    mcp_arguments={"platform": "twitter", "mode": "draft", "post_text": "Invoice created for a new AI Employee client.", "requires_hitl": False},
                    source_file=task.name,
                )

                class Result:
                    returncode = 0
                    stdout = ""
                    stderr = ""

                return Result()

            loop._run_codex = fake_codex  # type: ignore[method-assign]
            loop._refresh_dashboard = lambda: None  # type: ignore[method-assign]

            loop_result = loop.process_task(task)
            self.assertEqual(loop_result["status"], "approval_boundary")
            self.assertFalse(task.exists())
            self.assertEqual(len(list(pending.glob("APPROVAL_*.md"))), 3)

            for file_path in pending.glob("APPROVAL_*.md"):
                shutil.move(str(file_path), approved / file_path.name)

            hitl = HITLOrchestrator(str(vault))

            async def fake_call(*, server_name: str, tool_name: str, arguments: dict, **_kwargs):
                payload = {
                    "status": "ok",
                    "server_name": server_name,
                    "tool_name": tool_name,
                    "arguments": arguments,
                }
                if tool_name == "create_invoice":
                    payload = {"status": "created", "invoice_id": 101, "customer_name": arguments.get("customer_name", "ABC Traders")}
                elif tool_name == "send_email":
                    payload = {"status": "sent", "message_id": "msg_123"}
                elif tool_name == "browser_post_social":
                    payload = {"status": "draft_ready", "platform": arguments.get("platform", "twitter")}
                hitl._write_json_audit(
                    "mcp_call",
                    {
                        "status": "success",
                        "mcp_server": server_name,
                        "mcp_tool": tool_name,
                        "arguments": arguments,
                        "result": payload,
                    },
                )
                return payload

            hitl._call_mcp_tool_async = fake_call  # type: ignore[method-assign]
            processed = hitl.process_all_approved_once()
            self.assertEqual(processed, 3)

            json_logs = list((vault / "Logs").glob("*.json"))
            self.assertTrue(json_logs, "expected JSON audit log file")
            payload = json.loads(json_logs[0].read_text(encoding="utf-8"))
            mcp_call_events = [entry for entry in payload if entry.get("event_type") == "mcp_call"]
            self.assertGreaterEqual(len(mcp_call_events), 3)

            orchestrator = GoldOrchestrator(
                project_root=root,
                interval_seconds=1,
                force_weekly_audit=True,
                force_twitter=True,
            )
            orchestrator._handle_needs_action = lambda: None  # type: ignore[method-assign]
            orchestrator._handle_hitl_approved = lambda: None  # type: ignore[method-assign]
            orchestrator._handle_daily_linkedin = lambda: None  # type: ignore[method-assign]
            orchestrator._handle_weekly_social = lambda: None  # type: ignore[method-assign]

            def fake_skill(skill, _task: str):
                if skill == SKILL_WEEKLY_CEO_BRIEFING:
                    briefing = briefings / f"{datetime.now().strftime('%Y-%m-%d')}_CEO_Briefing.md"
                    briefing.write_text(
                        "# CEO Briefing\n\n## Revenue Overview\n- Invoiced: 50000 PKR\n",
                        encoding="utf-8",
                    )

            orchestrator._run_skill = fake_skill  # type: ignore[method-assign]
            orchestrator._handle_weekly_ceo_briefing()

            created_briefings = list(briefings.glob("*_CEO_Briefing.md"))
            self.assertEqual(len(created_briefings), 1)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GoldTierFlowTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
