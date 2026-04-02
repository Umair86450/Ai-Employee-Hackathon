# Gold Tier Autonomous Employee (Non-Technical Guide)

This repo delivers the **Gold Tier** self-driving employee. It watches Gmail/WhatsApp/files, turns customer work into Odoo invoices, routes approval-gated emails/social posts, logs every action, and produces a weekly CEO briefing. Everything you need is under `AI_Employee_Vault/` and the skills folder; no coding is required to run it once the environment is prepared.

## What’s here
- `AI_Employee_Vault/` – live state, approvals, logs, plans, briefings.
- `watchers/` – Gmail, WhatsApp, filesystem monitors that drop tasks into the vault.
- `orchestrator.py` + `ralph_loop.py` – the brain that reads tasks, makes plans, and creates approvals.
- `watchers/hitl_orchestrator.py` + `mcp_servers/` – execute approved external actions (Odoo, email, browser automation).
- `weekly_ceo_briefing.sh` – runs the CEO audit skill every Friday night.
- `.agents/skills/` – every action (email, invoice, social post) is defined as a reusable skill you can trigger.

## Preparation (one-time)
1. Open a terminal inside this folder:
   ```bash
   cd "/Users/mac/Desktop/P/Silver Tier/Ai-Employee-Hackathon/Gold Tier"
   ```
2. Install shared tooling:
   ```bash
   uv sync
   uv run playwright install chromium
   ```
3. Create a `.env` file (copy `.env.example`) and add your credentials (Odoo URL/API key, SMTP, social accounts). Do **not** commit this file.
4. Start the local Odoo stack:
   ```bash
   cd odoo19-local
   ./manage.sh up
   ```
   Wait a minute until the web container is healthy. Use `./manage.sh logs` to watch startup. Return to the root folder when ready.
5. Verify `.env` has `ODOO_URL`, `ODOO_DB`, `ODOO_API_KEY`, and any email or social credentials you plan to use.

## Run the Gold employee (daily)
1. Start the supervisor that runs all watchers:
   ```bash
   UV_CACHE_DIR=/tmp/uv-cache uv run python watchdog.py --project-root .
   ```
   Leave this terminal open; it will restart services if they crash.
2. In another terminal, list active files:
   ```bash
   UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --status
   ```
3. If you need to inject a manual request (for testing), create a markdown file:
   ```bash
   cat <<'EOF' > AI_Employee_Vault/Needs_Action/REQUEST.md
   # Client request
   Please create an Odoo invoice for ABC Traders, email it, and draft an X update.
   EOF
   ```
4. Check `AI_Employee_Vault/Pending_Approval/` – each sensitive action (email, Odoo, social) waits for your approval before execution.
5. Approve an action by moving the file to `/Approved/`:
   ```bash
   mv AI_Employee_Vault/Pending_Approval/APPROVAL_*.md AI_Employee_Vault/Approved/
   UV_CACHE_DIR=/tmp/uv-cache uv run python watchers/hitl_orchestrator.py --vault AI_Employee_Vault --process-once
   ```
   Logs and the approval file will record success or failure. If the MCP server fails due to Odoo being down, the approval moves into `AI_Employee_Vault/Queued/` for retry later.

## Weekly and recurring tasks
- Add the following cron entries (use `crontab -e`, replace `/ABS/PATH/TO/Silver Tier`):
  ```cron
  */5 * * * * cd /ABS/PATH/TO/Silver\ Tier && uv run orchestrator.py --project-root . --once >> AI_Employee_Vault/Logs/cron_orchestrator.log 2>&1
  0 22 * * 5 cd /ABS/PATH/TO/Silver\ Tier && ./weekly_ceo_briefing.sh >> AI_Employee_Vault/Logs/cron_weekly_ceo.log 2>&1
  ```
- Weekly CEO briefing attaches finance insights in `AI_Employee_Vault/Briefings/` and updates `AI_Employee_Vault/Dashboard.md`.

## Key folders you will use
- `AI_Employee_Vault/Needs_Action/` – incoming tasks from Gmail/WhatsApp or manual copies.
- `AI_Employee_Vault/Pending_Approval/` – approval requests await human review.
- `AI_Employee_Vault/Approved/` – once approved, actions get executed and logged.
- `AI_Employee_Vault/Logs/` – daily HTTPS-style log file plus JSON audit entries for MCP calls.
- `AI_Employee_Vault/Briefings/` – contains the latest CEO briefing and archives.
- `AI_Employee_Vault/Queued/` – failed/Odoo-unavailable approvals that will retry when you move them back to `Approved`.

## Testing
- Unit tests:
  ```bash
  python3 -m unittest discover -s tests
  ```
- End-to-end demo:
  ```bash
  python3 test_gold.py
  ```
  These commands run without any real network writes (external flows are stubbed), so they are safe for verification.

## Troubleshooting
- **Approval stuck in Pending:** Move it to `Approved/` once you verify the action details, then trigger `watchers/hitl_orchestrator.py`.
- **Odoo unreachable:** Check `odoo19-local/manage.sh logs` and restart `./manage.sh up`. Any approval that hit Odoo gets copied into `AI_Employee_Vault/Queued/`; move it back to `Approved/` after the service recovers.
- **Emails or social posts fail in MCP:** Check the inline JSON in the approval file, fix credentials in `.env`, and rerun the approved file.
- **Dashboard stale:** Run `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --update-dash`.

## Notes
- All AI logic lives in `.agents/skills/`. To add new capabilities, drop a new skill file and update the orchestrator references.
- Every sensitive action writes a markdown approval plus a JSON audit entry (`AI_Employee_Vault/Logs/<date>.json`) for traceability.
- Keep `.env` secret; do not commit it. The GitHub push already excludes runtime data (vault logs, approvals, Social_Summary entries, Odoo database files, WhatsApp session, etc.).

Need help with a flaky approval or social publish? Start with `AI_Employee_Vault/Logs/<today>.md` and work backwards from the MCP audit JSON file.
