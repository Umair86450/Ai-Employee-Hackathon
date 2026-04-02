---
name: weekly-ceo-briefing
description: Generate a weekly CEO briefing using Odoo accounting via odoo_mcp plus Business_Goals.md and completed work from AI_Employee_Vault/Done, then save the result in AI_Employee_Vault/Briefings/<YYYY-MM-DD>_CEO_Briefing.md. Use this for Friday executive review, weekly audit, or CEO summary requests.
---

# Weekly CEO Briefing

Run this workflow:

1. Read planning context:
   - `AI_Employee_Vault/Business_Goals.md`
   - `AI_Employee_Vault/Company_Handbook.md`
   - recent files in `AI_Employee_Vault/Done/`
   - latest entries from `AI_Employee_Vault/Logs/`
2. Read Odoo accounting via `odoo_mcp`:
   - call `generate_summary` for the last 7 days
   - call `read_transactions` for the last 7 days
   - call `search_records` on `account.move` to inspect posted vendor bills and other expense-side transactions
3. Build the weekly financial snapshot:
   - Revenue:
     - total invoiced this week
     - total paid this week
     - total outstanding receivables
   - Expenses:
     - total posted vendor bills / expense-side amounts identified from Odoo
     - notable recurring costs or suspicious charges
4. Read execution context from the vault:
   - summarize the most meaningful completed work from `AI_Employee_Vault/Done/`
   - identify bottlenecks from logs, pending approvals, or unfinished projects
5. Create:
   - `AI_Employee_Vault/Briefings/<YYYY-MM-DD>_CEO_Briefing.md`
6. Required sections:
   - Executive Summary
   - Revenue Overview
   - Expense Overview
   - Cash / Balance Signals
   - Completed This Week
   - Bottlenecks
   - Proactive Suggestions
   - Recommended Next 7 Days
7. After writing the briefing:
   - append a short log entry to `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md`
   - update `AI_Employee_Vault/Dashboard.md` with a note that the weekly CEO briefing was generated

Rules:
- Treat Odoo as the source of truth for accounting values.
- Treat `AI_Employee_Vault/` as the source of truth for operational progress.
- Keep the final briefing concise, executive-friendly, and specific.
