from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, patch
import sys


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

import main
from watchers.hitl_orchestrator import HITLOrchestrator


class HitlOrchestratorTests(unittest.TestCase):
    def test_approved_file_executes_only_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "AI_Employee_Vault"
            approved = vault / "Approved"
            approved.mkdir(parents=True, exist_ok=True)

            approval = approved / "APPROVAL_demo.md"
            approval.write_text(
                """---
request_id: demo
status: pending
created_at: 2026-04-01 09:00:00
action_type: payment
source_file: ""
mcp_server: payment_mcp
mcp_tool: process_payment
---

# Approval Request

## MCP Arguments
```json
{
  "payee": "Acme",
  "amount": 12.5
}
```
""",
                encoding="utf-8",
            )

            orchestrator = HITLOrchestrator(str(vault))
            orchestrator._call_mcp_tool_async = AsyncMock(  # type: ignore[method-assign]
                return_value={"status": "approved_for_manual_execution"}
            )

            orchestrator.process_approved_file(approval)
            orchestrator.process_approved_file(approval)

            content = approval.read_text(encoding="utf-8")
            self.assertIn("status: executed", content)
            self.assertEqual(content.count("## Execution Result"), 1)


class DashboardTests(unittest.TestCase):
    def test_update_dashboard_uses_live_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "AI_Employee_Vault"
            with patch.object(main, "VAULT_PATH", vault):
                main.ensure_vault_folders()
                (vault / "Needs_Action" / "task.md").write_text("demo", encoding="utf-8")
                (vault / "Plans" / "PLAN_demo.md").write_text("demo", encoding="utf-8")
                (vault / "Pending_Approval" / "APPROVAL_demo.md").write_text("demo", encoding="utf-8")

                main.update_dashboard()

                dashboard = (vault / "Dashboard.md").read_text(encoding="utf-8")
                self.assertIn("**Needs Action**: 1 files", dashboard)
                self.assertIn("**Plans**: 1 files", dashboard)
                self.assertIn("/Pending_Approval | 1 |", dashboard)


if __name__ == "__main__":
    unittest.main()
