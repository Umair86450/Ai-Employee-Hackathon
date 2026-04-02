# Check Status — Agent Skill

You are the AI Employee. Give a quick health check of the entire system.

## Your Task

1. **Check all vault folders** — list files in Inbox, Needs_Action, Done, Pending_Approval
2. **Read Dashboard.md** — when was it last updated?
3. **Check today's log** in `AI_Employee_Vault/Logs/<today>.md`
4. **Read Company_Handbook.md** — confirm you know the rules

## Report Format

Tell the user:
```
SYSTEM STATUS — <timestamp>
================================
/Inbox          : X files
/Needs_Action   : X files
/Done           : X files
/Pending_Approval: X files

Last Dashboard Update: <time>
Watcher: [Running / Unknown]

ACTION NEEDED:
- <list any items requiring human attention>

SYSTEM HEALTH: [OK / NEEDS ATTENTION]
```

## Rules
- Be concise — this is a quick check, not a full briefing
- If /Needs_Action has files, say "Run /process-inbox to handle them"
- If /Pending_Approval has files, list each one with required action
