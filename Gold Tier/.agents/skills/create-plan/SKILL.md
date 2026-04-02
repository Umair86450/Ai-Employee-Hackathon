---
name: create-plan
description: When markdown tasks arrive in AI_Employee_Vault/Needs_Action, read the handbook, create a timestamped plan in AI_Employee_Vault/Plans, mark whether approval is required, then hand off to SKILL_process_task.md.
---

# Create Plan (Silver Tier Reasoning Loop)

Use this workflow whenever any `.md` file appears in `AI_Employee_Vault/Needs_Action/`.

1. Read `AI_Employee_Vault/Company_Handbook.md` before taking action.
2. Find incoming `.md` files in `AI_Employee_Vault/Needs_Action/` and ignore `.gitkeep`.
3. For each file, read and extract:
   - Main objective
   - Key context and constraints
   - Whether the requested action is sensitive
4. Create a new plan file:
   - Path: `AI_Employee_Vault/Plans/PLAN_<YYYY-MM-DD_HHMMSS>.md`
   - Required sections:
     - `Objective`
     - `Steps` (checkbox list)
     - `Suggested Actions`
     - `Approval needed? Yes/No`
5. Use this template in the plan file:

```markdown
# PLAN_<YYYY-MM-DD_HHMMSS>

Source File: <filename>
Created At: <YYYY-MM-DD HH:MM:SS>

## Objective
<clear 1-3 sentence objective>

## Steps
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

## Suggested Actions
- Action 1
- Action 2
- Action 3

## Approval needed? Yes/No
- Reason: <why approval is or is not needed>
```

6. Approval decision rule:
   - Use `Yes` if the task includes any sensitive action from handbook policy (for example: posting on social media, sending messages, payments, deleting files, sharing personal information).
   - Otherwise use `No`.
7. After creating the plan, call `SKILL_process_task.md` to execute the task workflow.
8. Log the action in `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md` and update `AI_Employee_Vault/Dashboard.md` after significant progress.

Non-negotiable rules:
- Never delete original files.
- Always preserve auditability in logs.
- Never execute sensitive actions without explicit human approval.
