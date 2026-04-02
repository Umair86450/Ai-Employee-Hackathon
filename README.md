# AI-Employee-Hackathon

This repository contains two implementations of a local-first AI Employee project:

- `Bronze Tier/` for the basic single-watch flow
- `Silver Tier/` for the multi-watcher, planning, and approval workflow

## Repository Structure

```text
AI-Employee-Hackathon/
├── Bronze Tier/
└── Silver Tier/
```

## Bronze Tier

Bronze Tier is the simpler version of the project. It is focused on local file intake and task processing inside the vault.

Main capabilities:
- filesystem watcher for `Inbox/`
- creation of `Needs_Action/` items
- dashboard updates
- local-first processing flow

See the full guide in `Bronze Tier/README.md`.

## Silver Tier

Silver Tier is the more advanced workflow. It adds orchestrators, multiple watchers, planning, and human approval before sensitive actions.

Main capabilities:
- filesystem, Gmail, and WhatsApp watchers
- plan generation and workflow orchestration
- approval flow for sensitive actions
- LinkedIn drafting and publishing flow
- email MCP execution

Important:
- real secrets stay only in local `.env`
- committed setup example is available in `Silver Tier/.env.example`

See the full guide in `Silver Tier/README.md`.

## Quick Start

### Bronze Tier
```bash
cd "Bronze Tier"
uv sync
uv run main.py
```

### Silver Tier
```bash
cd "Silver Tier"
uv sync
uv run main.py
```

## Notes

- Open `AI_Employee_Vault/` in Obsidian if you want to inspect the workflow visually.
- `Silver Tier/.env` should not be committed.
- `Silver Tier/Ai-Employee-Hackathon-target/` is a local nested folder and is not part of the GitHub upload.
