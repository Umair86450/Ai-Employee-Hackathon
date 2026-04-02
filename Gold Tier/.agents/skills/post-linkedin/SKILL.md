---
name: post-linkedin
description: Create a sales-focused LinkedIn post (max 3000 chars) using Business_Goals.md and recent work context, then draft or publish via browser MCP with explicit human approval. Use this when asked to create or post LinkedIn content for the Digital AI Employee offer.
---

# Post LinkedIn (Silver Tier)

Use this workflow:

1. Read context:
   - `AI_Employee_Vault/Business_Goals.md`
   - Recent task context from latest files in `AI_Employee_Vault/Needs_Action/`, `AI_Employee_Vault/Done/`, or latest `AI_Employee_Vault/Logs/`.
2. Build the angle:
   - Sales-focused, professional, and outcome-oriented.
   - Default theme for this account: human support typically works ~8 hours/day, while a Digital AI Employee can operate 24/7.
   - Default language is English unless the user asks for Urdu/Hinglish.
3. Draft the LinkedIn post:
   - Hard limit: 3000 characters max.
   - Use: hook line, short value section, credibility statement, and CTA.
   - Include 3-8 relevant hashtags.
   - Do not invent fake stats, client names, or claims.
4. Generate image prompt for Codex image creation:
   - Match the post theme: "8-hour human shift vs 24/7 digital AI employee".
   - Keep visual style modern, clean, and business-focused.
5. Approval gate (required):
   - Posting on social media is sensitive and requires human approval.
   - Create `AI_Employee_Vault/Pending_Approval/LinkedIn_Post_<YYYY-MM-DD_HHMM>.md` containing:
     - Final post text
     - Image prompt
     - Proposed mode (`draft` or `publish`)
   - If explicit approval is not already present in chat, use `draft`.
6. MCP execution:
   - Output the final post text in chat.
   - Then call MCP tool: `browser_post_linkedin`.
   - Use payload like:

```json
{
  "mode": "draft",
  "post_text": "<final post text>",
  "image_prompt": "<codex image prompt>",
  "requires_hitl": true
}
```

7. Final response format:
   - `POST_TEXT:` (full final content)
   - `IMAGE_PROMPT:` (single prompt)
   - `MCP_TOOL_CALL:` `browser_post_linkedin(...)`
   - `STATUS:` `waiting_for_approval` or `posted`

Rules:
- Never publish without explicit user approval.
- Keep post content <= 3000 chars.
- If LinkedIn login/session fails, return draft output and approval-file path for manual next step.
