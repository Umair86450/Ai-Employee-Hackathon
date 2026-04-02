---
name: process-approved
description: Process approved HITL files by executing only actions already moved to AI_Employee_Vault/Approved, then log outcomes. Use this when Approved queue has APPROVAL_*.md files.
---

# Process Approved

Run this workflow:

1. Read `AI_Employee_Vault/Company_Handbook.md`.
2. Check `AI_Employee_Vault/Approved/` for `APPROVAL_*.md` files.
3. Execute approved actions by running:

```bash
uv run python watchers/hitl_orchestrator.py --vault AI_Employee_Vault --process-once
```

4. Verify results:
   - Successful execution details appended to approval file.
   - Failed executions moved to `AI_Employee_Vault/Rejected/`.
5. Refresh status via `.agents/skills/update-dashboard/SKILL_update_dashboard.md`.
6. Append relevant log notes in `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md`.

Rules:
- Never execute pending requests from `Pending_Approval`.
- Only process files already moved to `Approved`.
- Preserve full audit trail.
