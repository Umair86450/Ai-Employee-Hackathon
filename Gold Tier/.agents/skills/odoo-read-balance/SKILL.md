---
name: odoo-read-balance
description: Read invoice, payment, and outstanding balance information from Odoo through the Odoo MCP server. Use this when the user asks for account balances, receivables, or transaction summaries.
---

# Odoo Read Balance

Use this workflow:

1. Identify the reporting window:
   - default to the last 30 days
   - narrow by partner name if the user specifies a company
2. Call MCP tool `read_transactions` for detailed records.
3. Call MCP tool `generate_summary` for totals and open balance.
4. Return:
   - invoice count
   - payment count
   - total invoiced
   - total paid
   - total outstanding
   - top open invoices

Example tool payloads:

```json
{
  "days": 30,
  "partner_name": "ABC Traders",
  "limit": 20
}
```

```json
{
  "days": 30
}
```

Rules:
- Use `read_transactions` when the user needs record-level detail.
- Use `generate_summary` when the user needs balance or trend summaries.
- If the user asks for both, call both and combine the result.
