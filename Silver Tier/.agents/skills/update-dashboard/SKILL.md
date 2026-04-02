---
name: update-dashboard
description: Refresh AI_Employee_Vault/Dashboard.md with current folder counts, recent logs, pending approvals, and business-goal progress. Use this whenever the user asks to update dashboard, refresh status, or run update-dashboard.
---

# Update Dashboard

Execute these steps:

1. Read `AI_Employee_Vault/Company_Handbook.md`.
2. Count files in:
   - `AI_Employee_Vault/Inbox/`
   - `AI_Employee_Vault/Needs_Action/`
   - `AI_Employee_Vault/Done/`
   - `AI_Employee_Vault/Pending_Approval/`
   - `AI_Employee_Vault/Plans/`
3. Read the latest entries from `AI_Employee_Vault/Logs/` (last 5 actions).
4. Read `AI_Employee_Vault/Business_Goals.md`.
5. Rewrite `AI_Employee_Vault/Dashboard.md` with:
   - Current timestamp
   - System status summary
   - Folder counts
   - Recent activity
   - Items requiring owner attention
   - Goals progress snapshot
6. Log this update in `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md`.

Rules:
- Use the actual local date/time.
- If pending approvals exist, highlight them prominently.
- Keep output concise and scannable.

