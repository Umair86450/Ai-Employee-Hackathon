# Personal AI Employee — Bronze Tier

A local-first autonomous AI agent powered by **Claude Code** and **Obsidian**.

## What It Does
- **Watches** your `/Inbox` folder for new files
- **Creates** structured action files in `/Needs_Action`
- **Processes** tasks using Claude Code Agent Skills
- **Logs** every action for audit and review
- **Updates** your Dashboard in real-time

---

## Quick Start

### 1. Install dependencies
```bash
uv sync
```

### 2. Open vault in Obsidian
Open the `AI_Employee_Vault/` folder as an Obsidian vault.

### 3. Start the watcher
```bash
uv run main.py
```

### 4. Open Claude Code in this project
```bash
claude
```

### 5. Use Agent Skills
```
/check-status       → See system health
/process-inbox      → Process pending files
/update-dashboard   → Refresh dashboard
/morning-briefing   → Generate CEO briefing
```

---

## Architecture

```
Files dropped       Python Watcher      Claude Code         Obsidian Vault
in /Inbox     →    detects change  →   processes with  →   updated with
                   creates .md         Agent Skills        results
                   in /Needs_Action
```

## Folder Structure

```
AI_Employee_Vault/
├── Dashboard.md          ← Live status dashboard
├── Company_Handbook.md   ← Rules the AI follows
├── Business_Goals.md     ← Your business objectives
├── Inbox/                ← Drop files here
├── Needs_Action/         ← Pending AI processing
├── Done/                 ← Completed tasks
├── Plans/                ← AI-generated task plans
├── Pending_Approval/     ← Awaiting your approval
└── Logs/                 ← Daily audit logs
```

## Commands

| Command | Description |
|---------|-------------|
| `uv run main.py` | Start filesystem watcher |
| `uv run main.py --status` | Show vault stats |
| `uv run main.py --update-dash` | Update Dashboard.md |

## Security
- No credentials stored in vault
- All sensitive actions require human approval
- Full audit log in `/Logs/`
- Local-first: all data stays on your machine

---

**Hackathon**: Personal AI Employee Hackathon 0
**Tier**: Bronze
**Built with**: Claude Code + Obsidian + Python
