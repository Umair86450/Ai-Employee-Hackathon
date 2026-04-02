---
name: process-inbox
description: Process all pending markdown files in AI_Employee_Vault/Needs_Action by analyzing each item, creating a plan file, moving source files to Done, updating Dashboard.md, and appending today's log. Use this whenever the user asks to process inbox, pending files, or run the process-inbox workflow.
---

# Process Inbox

Follow this workflow exactly:

1. Read `AI_Employee_Vault/Company_Handbook.md`.
2. List all `.md` files in `AI_Employee_Vault/Needs_Action/` and ignore `.gitkeep`.
3. For each file:
   - Read and summarize what the file contains.
   - Decide recommended action and priority.
   - Create `AI_Employee_Vault/Plans/Plan_<filename>.md` with:
     - Summary
     - Recommended action
     - Priority
     - Risks/flags
   - If external or sensitive action is required, create an approval file in `AI_Employee_Vault/Pending_Approval/`.
   - Move the original file to `AI_Employee_Vault/Done/` (never delete permanently).
4. Rewrite `AI_Employee_Vault/Dashboard.md` with updated counts and recent activity.
5. Append an action entry to `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md`.

Non-negotiable rules:
- Never delete task files permanently.
- Never execute external sensitive actions without a pending approval file.
- Flag high-priority items clearly in dashboard/log output.

