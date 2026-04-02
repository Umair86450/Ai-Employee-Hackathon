---
name: odoo-create-invoice
description: Create a customer invoice in Odoo through the Odoo MCP server. Use this when the user wants an invoice created in the AI_Employee_Business database.
---

# Odoo Create Invoice

Use this workflow:

1. Confirm the invoice target:
   - Customer name or partner id
   - Line items
   - Invoice reference
   - Invoice date and due date if provided
2. Validate line items:
   - Each line must include `product_name` or `product_id`
   - Each line must include a positive quantity
   - Each line should include `price_unit`
3. Call MCP tool `create_invoice`.
4. Default behavior:
   - `journal_type`: `sale`
   - `post_immediately`: `true`
5. Return:
   - invoice id
   - invoice number
   - state
   - amount total
   - payment state

Example tool payload:

```json
{
  "customer_name": "ABC Traders",
  "ref": "AIE-INV-001",
  "post_immediately": true,
  "line_items": [
    {
      "product_name": "AI Employee Setup Fee",
      "quantity": 1,
      "price_unit": 120000
    },
    {
      "product_name": "AI Employee Subscription",
      "quantity": 1,
      "price_unit": 50000
    }
  ]
}
```

Rules:
- Do not guess a missing customer or product silently.
- If customer or product lookup is ambiguous, ask for clarification.
- Prefer posting the invoice immediately unless the user asks for a draft.
