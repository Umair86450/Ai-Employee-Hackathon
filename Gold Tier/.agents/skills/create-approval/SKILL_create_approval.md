---
name: create-approval
description: Create APPROVAL_*.md requests in AI_Employee_Vault/Pending_Approval for sensitive actions (email send, LinkedIn post, payment). Use this whenever external sensitive execution is requested so HITL approval happens before MCP execution.
---

# Create Approval (Silver Tier HITL)

Use this workflow whenever a task includes a sensitive action:
- `email_send`
- `linkedin_post`
- `payment`

1. Read `AI_Employee_Vault/Company_Handbook.md`.
2. Confirm the action is sensitive.
3. Build approval details:
   - Objective (what business outcome is needed)
   - Details (clear summary of what will happen)
   - MCP payload (exact tool arguments)
4. Create approval file in `AI_Employee_Vault/Pending_Approval/` by running:

```bash
uv run main.py --create-approval \
  --action-type "<email_send|linkedin_post|payment>" \
  --objective "<short objective>" \
  --details "<review details>" \
  --mcp-server "<optional override>" \
  --mcp-tool "<optional override>" \
  --mcp-args '<JSON payload>'
```

5. Do not execute MCP directly from this skill.
6. Wait for human decision:
   - Human approves by moving `APPROVAL_*.md` into `AI_Employee_Vault/Approved/`.
   - Orchestrator automatically executes MCP only after file is in `/Approved`.
   - Failed or invalid requests are moved to `AI_Employee_Vault/Rejected/`.

Rules:
- Never bypass HITL for sensitive actions.
- Keep MCP args complete and valid JSON.
- If a task is rejected, revise and create a new approval request.
