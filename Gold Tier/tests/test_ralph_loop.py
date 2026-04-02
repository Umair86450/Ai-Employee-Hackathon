from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ralph_loop import RalphLoop


class RalphLoopTests(unittest.TestCase):
    def _make_project(self, tmpdir: str) -> Path:
        root = Path(tmpdir)
        vault = root / "AI_Employee_Vault"
        for name in [
            "Needs_Action",
            "Done",
            "Pending_Approval",
            "Approved",
            "Rejected",
            "Logs",
        ]:
            (vault / name).mkdir(parents=True, exist_ok=True)
        (vault / "Company_Handbook.md").write_text("# Handbook\n", encoding="utf-8")
        (root / "main.py").write_text("print('stub')\n", encoding="utf-8")
        return root

    def test_detect_task_signals_defaults_generic_social_to_linkedin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._make_project(tmpdir)
            task = root / "AI_Employee_Vault" / "Needs_Action" / "TASK_demo.md"
            task.write_text(
                "# New launch task\nCreate invoice in Odoo, send email, and publish a social post.\n",
                encoding="utf-8",
            )
            loop = RalphLoop(project_root=root)
            signals = loop.detect_task_signals(task)

            self.assertTrue(signals.requires_invoice)
            self.assertTrue(signals.requires_email)
            self.assertEqual(signals.social_platforms, ("linkedin",))

    def test_process_task_auto_moves_file_when_approval_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._make_project(tmpdir)
            vault = root / "AI_Employee_Vault"
            task = vault / "Needs_Action" / "TASK_invoice.md"
            task.write_text("Create invoice and send email.\n", encoding="utf-8")

            loop = RalphLoop(project_root=root, max_attempts_per_task=1)

            def fake_codex(_prompt: str):
                approval = vault / "Pending_Approval" / "APPROVAL_demo.md"
                approval.write_text("demo", encoding="utf-8")

                class Result:
                    returncode = 0
                    stdout = ""
                    stderr = ""

                return Result()

            loop._run_codex = fake_codex  # type: ignore[method-assign]
            loop._refresh_dashboard = lambda: None  # type: ignore[method-assign]

            result = loop.process_task(task)

            self.assertEqual(result["status"], "approval_boundary")
            self.assertFalse(task.exists())
            self.assertTrue((vault / "Done" / "TASK_invoice.md").exists())


if __name__ == "__main__":
    unittest.main()
