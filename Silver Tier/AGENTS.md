# AGENTS.md

## Project Overview
Silver Tier AI Employee using `AI_Employee_Vault/` as the live runtime state. Watchers create work items, the orchestrator creates plans and routes tasks through skills, and sensitive actions go through HITL approval before MCP execution.

## Active Paths
- Runtime state: `AI_Employee_Vault/`
- Watchers: `watchers/`
- MCP servers: `mcp_servers/`
- Skills: `.agents/skills/`
- Main entrypoints: `main.py`, `orchestrator.py`, `daily_briefing.sh`
- Reference snapshots only: `Ai-Employee-Hackathon-target/`

## Core Rules
- Read `AI_Employee_Vault/Company_Handbook.md` before business-task processing.
- Treat `AI_Employee_Vault/` as the source of truth.
- Never delete business files permanently; move them to `AI_Employee_Vault/Done/`.
- Never execute sensitive actions directly; create approval files in `AI_Employee_Vault/Pending_Approval/`.
- Always update `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md` and `AI_Employee_Vault/Dashboard.md` after major workflow changes.
- Use existing skills in `.agents/skills/` instead of parallel custom agent logic.

## Engineering Rules
- Use Python for agent logic.
- Keep code modular, small, and single-responsibility.
- Use clear descriptive names.
- Keep prompts/templates separate from business logic when practical.
- Follow `input -> processing -> output`.
- Prefer OpenAI API for new AI integrations unless existing project-specific patterns should be extended.
- Validate AI outputs before downstream actions.
- Add basic error handling for API, auth, network, browser, and tool failures.
- Never hardcode secrets; use `.env` or local credential files.

## Workflow Rules
- Build automations as explicit step-by-step pipelines.
- Document workflow inputs, outputs, side effects, approval points, and failure paths.
- Prefer Zapier/Make when they solve the job cleanly; do not reimplement external automation logic without a reason.
- Test each new agent/workflow with at least 2 realistic use cases when feasible.
- Add lightweight tests in `tests/` for orchestrator, approval, and state logic where practical.
- Log useful inputs/outputs for debugging without exposing secrets.
- Keep logs, dashboard, and approval files consistent.

## Key Commands
- `uv sync`
- `uv run playwright install chromium`
- `uv run main.py`
- `uv run main.py --status`
- `uv run main.py --run-orchestrator`
- `uv run main.py --run-hitl`
- `uv run orchestrator.py --project-root . --once`
- `uv run orchestrator.py --project-root . --once --force-linkedin`
- `python3 -m unittest discover -s tests`

## Important Notes
- No active `LinkedInWatcher.py`; LinkedIn flow is driven by `orchestrator.py`, `daily_briefing.sh`, and `mcp_servers/linkedin_mcp.py`.
- `main.py` starts Gmail watcher only if `AI_Employee_Vault/credentials.json` exists.
- First Gmail run writes `AI_Employee_Vault/token.json`.
- First WhatsApp run requires QR and persists session in `whatsapp_session/`.
- LinkedIn publish requires `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD`.
- Email MCP requires SMTP creds in `.env`.

## On-Demand Docs
- Setup/runbook: `README.md`
- Business rules: `AI_Employee_Vault/Company_Handbook.md`
- Scheduling: `ops/cron.example`
