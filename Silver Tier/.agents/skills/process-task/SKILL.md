---
name: process-task
description: Execute task processing for current Needs_Action items after planning. Use this when create-plan has prepared a plan and tasks now need execution while respecting approval policies.
---

# Process Task

Follow this workflow:

1. Read `AI_Employee_Vault/Company_Handbook.md`.
2. Inspect current files in `AI_Employee_Vault/Needs_Action/` (ignore `.gitkeep`).
3. Ensure each pending item has a corresponding plan in `AI_Employee_Vault/Plans/`.
4. Execute processing by following `.agents/skills/process-inbox/SKILL.md` exactly.
5. If any sensitive external action is required, create approval request using `.agents/skills/create-approval/SKILL_create_approval.md` and do not execute directly.
6. Refresh status by following `.agents/skills/update-dashboard/SKILL_update_dashboard.md`.

Rules:
- Never bypass human approval for sensitive actions.
- Never delete source files permanently.
- Keep logs and dashboard updated.
