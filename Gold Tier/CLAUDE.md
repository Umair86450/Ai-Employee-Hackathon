# AGENTS.md

## Scope
This repo targets a Gold Tier Autonomous Employee. Gold Tier means Silver still works, plus cross-domain Personal + Business workflows, local Odoo Community accounting via JSON-RPC for Odoo 19+, Facebook/Instagram posting + summaries, Twitter (X) posting + summaries, multiple MCP servers by action type, weekly Business and Accounting Audit with CEO briefing, graceful degradation, comprehensive audit logging, Ralph Wiggum loop autonomy, and architecture/lessons-learned documentation.

## Source Of Truth
- Read `AI_Employee_Vault/Company_Handbook.md` before business-task work.
- `AI_Employee_Vault/` is the runtime source of truth for plans, approvals, logs, dashboard, and outputs.
- Never delete business files permanently; move them to `AI_Employee_Vault/Done/`.

## Operating Model
- Watchers create work items.
- The orchestrator plans, routes, retries, and records outcomes.
- Skills do AI reasoning and generation.
- MCP servers do deterministic external actions.
- New AI-powered functionality must be implemented as Agent Skills, not ad hoc prompt logic.
- Do not put AI decision-making inside MCP servers.
- Prefer extending the orchestrator/skill model over side-channel automation.

## Guardrails
- Sensitive external actions must go through `AI_Employee_Vault/Pending_Approval/`.
- Update `AI_Employee_Vault/Logs/<YYYY-MM-DD>.md` and `AI_Employee_Vault/Dashboard.md` after major workflow changes.
- Never report an external action as successful if it did not actually succeed.
- If credentials, APIs, or integrations fail, log the issue, degrade gracefully, and continue unaffected workflows where possible.

## Ralph Wiggum Loop
- For autonomous multi-step work: inspect current state and goal, choose the next best action, execute via skill or MCP tool, validate the result, log the outcome, then retry, recover, escalate, or continue until completion.
- Stop cleanly on approval boundaries, missing credentials, policy restrictions, or repeated failure thresholds.
- Every loop iteration must be traceable in logs.

## Conventions
- Keep workflows explicit, resumable, and auditable.
- Keep workflow-critical orchestration in Python.
- Validate AI outputs before downstream actions.
- Use multiple MCP servers for distinct domains such as communications, social, accounting, and payments.

## Key Paths
- Runtime state: `AI_Employee_Vault/`
- Skills: `.agents/skills/`
- MCP servers: `mcp_servers/`
- Entrypoints: `main.py`, `orchestrator.py`, `daily_briefing.sh`
- Tests: `tests/`

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
