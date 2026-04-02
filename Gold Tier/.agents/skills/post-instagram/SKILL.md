---
name: post-instagram
description: Generate a business Instagram caption from Business_Goals.md, attach an image when available, and send it through browser_mcp in draft or publish mode. Use this for Instagram promotion of the Digital AI Employee offer.
---

# Post Instagram

Use this workflow:

1. Read business context:
   - `AI_Employee_Vault/Business_Goals.md`
   - latest relevant updates from `AI_Employee_Vault/Logs/` or `Done/`
2. Draft the caption:
   - concise, business-focused, readable on mobile
   - oriented around the Digital AI Employee offer
   - include a short CTA
   - include 3-8 relevant hashtags
3. Image requirement:
   - Instagram publishing needs an image
   - if no image path is provided, stay in `draft` mode and return an image prompt
4. Approval gate:
   - social posting is sensitive
   - unless the user explicitly approves publish, use `draft`
   - create an approval request in `AI_Employee_Vault/Pending_Approval/` with action type `instagram_post`
5. MCP execution:
   - call `browser_post_social` via `browser_mcp`
   - use payload like:

```json
{
  "platform": "instagram",
  "mode": "draft",
  "post_text": "<final caption>",
  "image_prompt": "<image prompt>",
  "image_path": null,
  "requires_hitl": true
}
```

6. After MCP execution:
   - return the caption
   - return the social summary path created under `Social_Summary/`

Rules:
- Never publish without explicit user approval.
- Do not attempt Instagram publish without an image.
- If publish fails, return the error and the saved summary path.
