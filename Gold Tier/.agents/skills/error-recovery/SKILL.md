---
name: error-recovery
description: Recover Gold Tier workflow failures by checking MCP audit logs, queued Odoo approvals, retryable errors, and watchdog-managed services. Use this when Odoo is down, MCP calls are failing, services keep crashing, or the owner asks for resilience/debug recovery steps.
---

# Error Recovery

Use this workflow for Gold Tier runtime failures.

1. Read:
   - `AI_Employee_Vault/Company_Handbook.md`
   - today's `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md`
   - today's `AI_Employee_Vault/Logs/<YYYY-MM-DD>.json`
2. Check `AI_Employee_Vault/Queued/` for degraded Odoo approvals.
3. For MCP failures:
   - identify the latest `mcp_call` entries in the JSON audit log
   - separate transient errors from permanent validation/policy errors
4. For transient errors:
   - rely on `retry_handler.py` behavior first
   - if retries are exhausted and the action is Odoo-related, keep the queued file in `AI_Employee_Vault/Queued/`
   - tell the owner how to move the queued file back to `Approved/` after Odoo recovers
5. For service crashes:
   - inspect `watchdog.py` logs and supervised process state
   - restart with `python3 watchdog.py --project-root .`
6. Update:
   - `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md`
   - `AI_Employee_Vault/Dashboard.md`

Important rules:
- Never mark a failed external action as successful.
- Never delete approval files; move or keep them in vault state folders.
- Keep explanations short and action-oriented.
