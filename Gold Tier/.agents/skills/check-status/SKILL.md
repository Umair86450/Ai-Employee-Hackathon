---
name: check-status
description: Produce a quick system health report by checking vault folder counts, dashboard recency, and today's logs. Use this whenever the user asks for status check, health check, or check-status.
---

# Check Status

Steps:

1. Read `AI_Employee_Vault/Company_Handbook.md`.
2. Count files in:
   - `AI_Employee_Vault/Inbox/`
   - `AI_Employee_Vault/Needs_Action/`
   - `AI_Employee_Vault/Done/`
   - `AI_Employee_Vault/Pending_Approval/`
3. Read `AI_Employee_Vault/Dashboard.md` and capture last update time.
4. Read today's log file `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md` if present.
5. Return a concise report with:
   - Timestamp
   - Folder counts
   - Last dashboard update
   - Required human actions
   - `SYSTEM HEALTH: OK` or `SYSTEM HEALTH: NEEDS ATTENTION`

Rules:
- If `Needs_Action` has files, explicitly recommend running process-inbox.
- If `Pending_Approval` has files, list each item and needed owner action.

