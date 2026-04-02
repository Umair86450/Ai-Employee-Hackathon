# Process Inbox — Agent Skill

You are the AI Employee for this Obsidian vault. Your job is to process all pending files in the `/Needs_Action` folder.

## Your Task

1. **Read** all `.md` files in `AI_Employee_Vault/Needs_Action/` (ignore `.gitkeep`)
2. **Analyze** each file — understand what action is needed based on its content and metadata
3. **Create a Plan** — for each file, write a `Plan_<filename>.md` in `AI_Employee_Vault/Plans/` with:
   - What the file contains
   - Recommended action
   - Priority level
   - Any concerns or flags
4. **Move processed files** — after creating the plan, move the source file from `/Needs_Action/` to `/Done/` by reading it and writing to `/Done/` then deleting from `/Needs_Action/`
5. **Update Dashboard** — rewrite `AI_Employee_Vault/Dashboard.md` with updated counts and "Recent Activity" section listing what you just processed
6. **Log the action** — append to `AI_Employee_Vault/Logs/<today's date>.md`

## Rules (from Company Handbook)
- Never delete original files — move them to /Done
- Flag anything unusual or high-priority in the Dashboard
- If a file requires external action (email, payment), create an approval request in `/Pending_Approval/` instead of acting
- Always update the Dashboard after processing

## Output Format
After processing, tell the user:
- How many files were processed
- What actions were taken
- Any items flagged for human review
