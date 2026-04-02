# Update Dashboard — Agent Skill

You are the AI Employee. Update the `AI_Employee_Vault/Dashboard.md` file with the current state of the vault.

## Your Task

1. **Count files** in each folder:
   - `AI_Employee_Vault/Inbox/` — files waiting to be picked up
   - `AI_Employee_Vault/Needs_Action/` — files pending processing
   - `AI_Employee_Vault/Done/` — completed files
   - `AI_Employee_Vault/Pending_Approval/` — awaiting human approval
   - `AI_Employee_Vault/Plans/` — active plans

2. **Read recent logs** from `AI_Employee_Vault/Logs/` — get the last 5 log entries

3. **Read Business_Goals.md** to check if any goals need attention

4. **Rewrite Dashboard.md** with:
   - Current date and time
   - System status table
   - File counts per folder
   - Recent activity (last 5 actions from logs)
   - Any urgent items that need human attention
   - Progress toward business goals

## Dashboard Format

```markdown
# AI Employee Dashboard
---
last_updated: <ISO timestamp>
---

## System Status
(table with component status)

## Vault Summary
(counts for each folder)

## Recent Activity
(last 5 log entries)

## Needs Your Attention
(any items in /Pending_Approval or flagged HIGH priority)

## Business Goals Progress
(brief summary from Business_Goals.md)

---
*Updated by AI Employee — <timestamp>*
```

## Rules
- Always use today's actual date and time
- If /Pending_Approval has files, highlight them prominently
- Keep the dashboard concise and scannable
