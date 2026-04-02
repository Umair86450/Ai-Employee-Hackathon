---
name: post-twitter
description: Generate a business X/Twitter post or thread from recent business activity, post it through browser_mcp or the X API when write credentials are available, then update Social_Summary/X_Summary.md and the weekly audit trail. Use this for Gold Tier Digital AI Employee posting on X.
---

# Post Twitter / X

Use this workflow:

1. Read source context:
   - `AI_Employee_Vault/Business_Goals.md`
   - latest relevant entries from `AI_Employee_Vault/Logs/`
   - recent completed work from `AI_Employee_Vault/Done/` when needed
2. Build the post angle:
   - focus on real recent business activity, progress, launches, integrations, or automation wins
   - default theme is the Digital AI Employee offer and recent Gold Tier execution
   - do not invent customer names, metrics, or claims
3. Choose post format:
   - use a single post when one clear update fits in one message
   - use a thread when there are 2-5 short points that read better as a sequence
   - default to a single post unless a thread is clearly better
4. Draft the content:
   - keep each post concise and business-focused
   - include a short CTA when useful
   - include 1-4 relevant hashtags at most
   - avoid spammy formatting
5. Choose posting transport:
   - prefer X API only when write-capable credentials are available
   - for X API posting, require user-context write credentials, not just a read-only bearer token
   - if no X write credentials are available, use `browser_mcp` only if it supports X posting in the current environment
   - if neither is available, stop at draft mode and save the summary
6. Approval gate:
   - external social posting is sensitive
   - unless explicit approval already exists in chat, use `draft`
   - create an approval request in `AI_Employee_Vault/Pending_Approval/` with action type `twitter_post`
   - include final post text, thread parts if any, image path if any, chosen transport, and proposed mode
7. Execute:
   - if using browser automation, call the browser MCP tool for X posting with the final text
   - if using the X API, post the single tweet or post the thread in order
   - if an image is provided, attach it when the chosen transport supports it
8. After posting or drafting:
   - create or update `Social_Summary/X_Summary.md`
   - append a new section with:
     - timestamp
     - mode: `draft` or `publish`
     - transport: `x_api`, `browser_mcp`, or `draft_only`
     - format: `single_post` or `thread`
     - final post text or numbered thread parts
     - image path if any
     - returned post URL or IDs if available
     - fetched replies or response summary if available
     - status: `draft_ready`, `posted`, or `failed`
9. Weekly audit integration:
   - append a short audit note to `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md`
   - update `AI_Employee_Vault/Dashboard.md` recent activity with a one-line X workflow note when a real post or fresh draft is created
   - in `Social_Summary/X_Summary.md`, keep a final section named `## Weekly Audit Notes` summarizing:
     - latest X activity this week
     - number of posts/threads created this week
     - pending approvals if any
     - notable replies or engagement if available

## Output Format

Return:

- `FORMAT:` `single_post` or `thread`
- `TRANSPORT:` `x_api`, `browser_mcp`, or `draft_only`
- `MODE:` `draft` or `publish`
- `POST_TEXT:` final single post, or numbered thread parts
- `SUMMARY_FILE:` path to `Social_Summary/X_Summary.md`
- `STATUS:` `draft_ready`, `posted`, or `failed`

## Transport Rules

### X API

Use only when write-capable credentials are present. Read-only bearer tokens are not enough for publishing.

Acceptable examples:

- OAuth 1.0a app/user tokens
- OAuth 2 user-context write tokens

If the available credentials are unclear, do not guess. Fall back to draft mode or browser automation if already supported.

### browser_mcp

Use only when the browser MCP in the current repo/config explicitly supports X posting. If it currently supports only other social platforms, do not pretend it supports X. Fall back to draft mode and state the limitation clearly.

## Summary File Template

When writing `Social_Summary/X_Summary.md`, append entries using this structure:

```md
## 2026-04-02 16:30:00
- Mode: `draft`
- Transport: `draft_only`
- Format: `single_post`
- Status: `draft_ready`
- URL/IDs: ``
- Image Path: ``

### Post Text
<final post text or thread parts>

### Replies / Response Summary
- none yet
```

At the bottom, keep or refresh:

```md
## Weekly Audit Notes
- Latest X activity: ...
- Posts this week: ...
- Pending approvals: ...
- Notable replies: ...
```

## Rules

- Never publish without explicit user approval.
- Never invent engagement, replies, or metrics.
- Prefer recent real business activity over generic marketing copy.
- If there is no X write path available, still produce the draft and update `Social_Summary/X_Summary.md`.
- If using a thread, keep it tight and coherent. Avoid long filler threads.
