---
name: post-facebook
description: Generate a business Facebook post from Business_Goals.md, attach an image if provided, and send it through browser_mcp in draft or publish mode. Use this for Facebook marketing posts for the Digital AI Employee offer.
---

# Post Facebook

Use this workflow:

1. Read business context:
   - `AI_Employee_Vault/Business_Goals.md`
   - recent work context from the latest `AI_Employee_Vault/Logs/` or `Done/`
2. Draft a business post:
   - professional and sales-focused
   - based on the Digital AI Employee offer
   - keep under 3000 characters
   - default language is English unless the user asks otherwise
3. Optional image:
   - if the user provides an image path, use it
   - otherwise generate only an image prompt and leave `image_path` empty
4. Approval gate:
   - social posting is sensitive
   - unless the user explicitly approves publish, use `draft`
   - create an approval request in `AI_Employee_Vault/Pending_Approval/` with action type `facebook_post`
5. MCP execution:
   - call `browser_post_social` via `browser_mcp`
   - use payload like:

```json
{
  "platform": "facebook",
  "mode": "draft",
  "post_text": "<final post text>",
  "image_prompt": "<optional image prompt>",
  "image_path": null,
  "requires_hitl": true
}
```

6. After MCP execution:
   - return the generated post text
   - return the social summary path created under `Social_Summary/`

Rules:
- Never publish without explicit user approval.
- Do not invent claims, stats, or clients.
- If publish fails, return the error and the saved summary path.
