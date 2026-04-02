from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
import sys
from unittest.mock import patch


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

from audit_logger import append_json_log
from watchers.hitl_orchestrator import HITLOrchestrator


class AuditLoggerTests(unittest.TestCase):
    def test_append_json_log_creates_daily_array(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir)
            append_json_log(logs_dir, {"event_type": "demo", "status": "ok"})
            path = next(logs_dir.glob("*.json"))
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["event_type"], "demo")
            self.assertEqual(payload[0]["status"], "ok")


class QueueFallbackTests(unittest.TestCase):
    def test_odoo_transient_failure_moves_approval_to_queued(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "AI_Employee_Vault"
            approved = vault / "Approved"
            approved.mkdir(parents=True, exist_ok=True)

            approval = approved / "APPROVAL_odoo.md"
            approval.write_text(
                """---
request_id: demo-odoo
status: pending
created_at: 2026-04-02 18:00:00
action_type: odoo_create_invoice
source_file: ""
mcp_server: odoo_mcp
mcp_tool: create_invoice
---

# Approval Request

## MCP Arguments
```json
{
  "customer_name": "ABC Traders",
  "line_items": []
}
```
""",
                encoding="utf-8",
            )

            orchestrator = HITLOrchestrator(str(vault))

            async def failing_call(**_kwargs):
                raise RuntimeError("Unable to reach Odoo at http://localhost:8069: connection refused")

            orchestrator._call_mcp_tool_async = failing_call  # type: ignore[method-assign]

            orchestrator.process_approved_file(approval)

            queued = vault / "Queued" / "APPROVAL_odoo.md"
            self.assertFalse(approval.exists())
            self.assertTrue(queued.exists())
            self.assertIn("status: queued", queued.read_text(encoding="utf-8"))

    def test_error_payload_rejects_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "AI_Employee_Vault"
            approved = vault / "Approved"
            approved.mkdir(parents=True, exist_ok=True)

            approval = approved / "APPROVAL_email.md"
            approval.write_text(
                """---
request_id: demo-email
status: pending
created_at: 2026-04-02 18:00:00
action_type: email_send
source_file: ""
mcp_server: email_mcp
mcp_tool: send_email
---

# Approval Request

## MCP Arguments
```json
{
  "to": "demo@example.com",
  "subject": "Test",
  "body": "Hello"
}
```
""",
                encoding="utf-8",
            )

            orchestrator = HITLOrchestrator(str(vault))

            async def failing_payload(**_kwargs):
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": "EMAIL_SMTP_USERNAME is required"}],
                }

            orchestrator._call_mcp_tool_async = failing_payload  # type: ignore[method-assign]

            orchestrator.process_approved_file(approval)

            rejected = vault / "Rejected" / "APPROVAL_email.md"
            self.assertFalse(approval.exists())
            self.assertTrue(rejected.exists())
            self.assertIn("status: rejected", rejected.read_text(encoding="utf-8"))

    def test_compose_mcp_env_loads_project_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            vault = project_root / "AI_Employee_Vault"
            vault.mkdir(parents=True, exist_ok=True)
            (project_root / ".env").write_text(
                "EMAIL_SMTP_USERNAME=tester@example.com\nEMAIL_SMTP_PASSWORD=secret\n",
                encoding="utf-8",
            )

            orchestrator = HITLOrchestrator(str(vault))
            with patch.dict("os.environ", {}, clear=True):
                env = orchestrator._compose_mcp_env({"env": {"EMAIL_SMTP_HOST": "smtp.gmail.com"}})

            self.assertEqual(env["EMAIL_SMTP_USERNAME"], "tester@example.com")
            self.assertEqual(env["EMAIL_SMTP_PASSWORD"], "secret")
            self.assertEqual(env["EMAIL_SMTP_HOST"], "smtp.gmail.com")


if __name__ == "__main__":
    unittest.main()
