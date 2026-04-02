---
name: morning-briefing
description: Generate a CEO morning briefing from AI_Employee_Vault state (goals, completed work, pending work, approvals, logs), save it in Briefings, and update dashboard/logs. Use this whenever the user asks for morning briefing, daily briefing, or executive summary.
---

# Morning Briefing

Run this workflow:

1. Read:
   - `AI_Employee_Vault/Business_Goals.md`
   - `AI_Employee_Vault/Company_Handbook.md`
   - Files in `AI_Employee_Vault/Done/`
   - Files in `AI_Employee_Vault/Needs_Action/`
   - Files in `AI_Employee_Vault/Pending_Approval/`
   - Latest log entries in `AI_Employee_Vault/Logs/`
2. Analyze:
   - Recent completions
   - Pending items
   - Bottlenecks/risks
   - Patterns worth action
3. Create `AI_Employee_Vault/Briefings/<YYYY-MM-DD>_Morning_Briefing.md`.
4. Include sections:
   - Executive Summary
   - Completed Recently
   - Pending Items
   - Needs Your Approval
   - Bottlenecks / Flags
   - Proactive Suggestions (1-3)
5. Update `AI_Employee_Vault/Dashboard.md` with briefing-generated note.
6. Append a log entry in `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md`.

Rules:
- Keep it executive-friendly: concise and actionable.
- Put urgent items at the top.
- Include specific names, deadlines, or amounts when available.

