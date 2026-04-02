# Personal AI Employee — Silver Tier

Local-first AI assistant built around `AI_Employee_Vault/`, Codex skills, Python watchers, and HITL approvals.

This repo is for the Silver Tier workflow:
- multiple watchers
- plan generation
- approval-based external actions
- LinkedIn drafting/post flow
- email MCP execution

## What This Project Does
End-to-end flow:

1. A watcher detects something new.
2. It creates a file in `AI_Employee_Vault/Needs_Action/`.
3. The Silver orchestrator creates a plan in `AI_Employee_Vault/Plans/`.
4. If the task is sensitive, an approval file is created in `AI_Employee_Vault/Pending_Approval/`.
5. Human approves by moving that file to `AI_Employee_Vault/Approved/`.
6. HITL orchestrator executes the approved MCP action.
7. Logs and dashboard are updated.

## Main Components
- `watchers/filesystem_watcher.py`
  Watches local `Inbox/`.
- `watchers/GmailWatcher.py`
  Polls Gmail unread/important emails and writes `EMAIL_*.md`.
- `watchers/WhatsAppWatcher.py`
  Reads unread WhatsApp Web chats and writes `WHATSAPP_*.md`.
- `orchestrator.py`
  Runs the Silver skill loop for plans, task processing, dashboard refresh, and LinkedIn drafting.
- `watchers/hitl_orchestrator.py`
  Executes only approved sensitive actions.
- `mcp_servers/email_mcp.py`
  Sends real email through SMTP.
- `mcp_servers/linkedin_mcp.py`
  Creates draft or publish LinkedIn posts through Playwright.

## Vault Structure
```text
AI_Employee_Vault/
├── Dashboard.md
├── Company_Handbook.md
├── Business_Goals.md
├── Inbox/
├── Needs_Action/
├── Done/
├── Plans/
├── Pending_Approval/
├── Approved/
├── Rejected/
├── Logs/
└── Assets/
```

## One-Time Setup
### 1. Install Python dependencies
```bash
uv sync
```

### 2. Install Playwright browser support
Required for WhatsApp and LinkedIn browser automation.

```bash
uv run playwright install chromium
```

If Chrome is already installed on your machine, WhatsApp watcher will try to use it first.

### 3. Open the vault
Open `AI_Employee_Vault/` in Obsidian if you want to monitor files visually.

### 4. Create a local `.env`
Create `.env` in project root if you want email sending and LinkedIn publishing.

Example:
```env
EMAIL_SMTP_USERNAME=your_email@gmail.com
EMAIL_SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com

LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password
LINKEDIN_HEADLESS=false
```

Notes:
- For Gmail SMTP, use an app password if your Gmail account has 2FA enabled.
- `.env` is local only and should not be committed.

## Fast Start
### Run the full Silver stack
This starts:
- filesystem watcher
- Gmail watcher if `AI_Employee_Vault/credentials.json` exists
- WhatsApp watcher
- HITL orchestrator
- Silver skill orchestrator

```bash
uv run main.py
```

### Useful control commands
```bash
uv run main.py --status
uv run main.py --update-dash
uv run main.py --run-orchestrator
uv run main.py --run-hitl
```

### Start full stack but disable some services
Examples:
```bash
uv run main.py --no-gmail
uv run main.py --no-whatsapp
uv run main.py --no-hitl
uv run main.py --no-skill-loop
```

## Gmail Watcher Setup
This watcher reads unread and important Gmail messages and writes them into `Needs_Action/`.

### Step 1. Enable Gmail API
In Google Cloud Console:

1. Create a project.
2. Enable the Gmail API.
3. Create OAuth credentials for a Desktop App.
4. Download the OAuth JSON file.

### Step 2. Put credentials in the vault
Save the downloaded file as:

```text
AI_Employee_Vault/credentials.json
```

### Step 3. Run Gmail watcher
```bash
uv run python watchers/GmailWatcher.py --vault AI_Employee_Vault --interval 120
```

### Step 4. Complete first-time Google login
On first run:
- a browser window opens
- sign in to Gmail
- grant access
- token will be saved to:

```text
AI_Employee_Vault/token.json
```

### Step 5. Verify output
New Gmail items appear like:
- `AI_Employee_Vault/Needs_Action/EMAIL_<message_id>.md`

### If you want Gmail watcher inside full stack
Just run:
```bash
uv run main.py
```

Important:
- `main.py` will skip Gmail watcher automatically if `credentials.json` is missing.

## WhatsApp Watcher Setup
This watcher reads unread WhatsApp Web chats using Playwright.

### Step 1. Install Playwright browser
```bash
uv run playwright install chromium
```

### Step 2. Run WhatsApp watcher manually
```bash
uv run python watchers/WhatsAppWatcher.py --vault AI_Employee_Vault --interval 60
```

### Step 3. First run login
On first run:
- browser opens visibly
- WhatsApp Web loads
- scan QR code with your phone

Session data is saved in:
```text
whatsapp_session/
```

After successful login:
- later runs can use saved session
- watcher can continue without QR

### Recommended mode
To reduce noisy unread-only alerts, use keyword filtering:

```bash
uv run python watchers/WhatsAppWatcher.py --vault AI_Employee_Vault --interval 60 --require-keywords
```

### Debug mode
If watcher is not detecting unread chats correctly:
```bash
uv run python watchers/WhatsAppWatcher.py --vault AI_Employee_Vault --debug-unread
```

### Verify output
New WhatsApp items appear like:
- `AI_Employee_Vault/Needs_Action/WHATSAPP_<contact>.md`

## Filesystem Watcher Setup
This watcher reads local files dropped into `Inbox/`.

### Run manually
```bash
uv run python watchers/filesystem_watcher.py --vault AI_Employee_Vault
```

### How it works
1. Drop a file into `AI_Employee_Vault/Inbox/`
2. Watcher copies metadata into `AI_Employee_Vault/Needs_Action/`
3. Original file is preserved

## LinkedIn Workflow Setup
Important:
- there is no separate `LinkedInWatcher.py` in this repo
- LinkedIn is handled by the Silver skill workflow plus scheduler

So LinkedIn flow here means:
- generate draft automatically
- create approval request
- publish only after approval

### Step 1. Add LinkedIn credentials to `.env`
```env
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password
LINKEDIN_HEADLESS=false
```

Use `LINKEDIN_HEADLESS=false` during debugging or first publish attempts.

### Step 2. Run one forced LinkedIn cycle
This tells the orchestrator to create the daily LinkedIn draft/approval now.

```bash
uv run orchestrator.py --project-root . --once --force-linkedin
```

### Step 3. Check pending approvals
Look in:
```text
AI_Employee_Vault/Pending_Approval/
```

You should see an `APPROVAL_*linkedin_post*.md` file.

### Step 4. Human approval
If the draft looks good:
- move the file from `Pending_Approval/` to `Approved/`

Example:
```bash
mv AI_Employee_Vault/Pending_Approval/APPROVAL_..._linkedin_post.md AI_Employee_Vault/Approved/
```

### Step 5. Execute approved LinkedIn action
If HITL orchestrator is already running:
```bash
uv run main.py --run-hitl
```

Or if full stack is running, it will pick approved items automatically.

### Draft-only daily workflow
You can also run:
```bash
./daily_briefing.sh
```

This script:
- refreshes dashboard
- checks if LinkedIn draft is needed
- creates approval request only

### Force daily briefing to create LinkedIn request
```bash
FORCE_LINKEDIN=1 ./daily_briefing.sh
```

## Plan Generation Workflow
Silver tier requires plans.

When `Needs_Action/` has files, the orchestrator:
1. bootstraps plan files
2. runs `create-plan` skill
3. runs `process-task` skill
4. refreshes dashboard

### Run one orchestration cycle manually
```bash
uv run orchestrator.py --project-root . --once
```

### Verify plan output
Look in:
```text
AI_Employee_Vault/Plans/
```

## HITL Approval Workflow
Sensitive actions are never supposed to execute directly.

### Step-by-step
1. Task arrives in `Needs_Action/`
2. Skill/orchestrator decides action is sensitive
3. Approval file is created in `Pending_Approval/`
4. Human reviews file
5. Human moves file to `Approved/`
6. HITL orchestrator executes MCP tool
7. Result is appended to the approval file
8. Failed approvals go to `Rejected/`

### Run approval processor only
```bash
uv run main.py --run-hitl
```

## Email MCP Setup
This is the external action server for sending real email.

### Required `.env`
```env
EMAIL_SMTP_USERNAME=your_email@gmail.com
EMAIL_SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
```

Optional:
```env
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USE_TLS=true
```

### How email is normally used
- system creates `APPROVAL_*email_send*.md`
- human approves
- HITL executes `send_email`

## Scheduling With Cron
Sample cron file is here:
```text
ops/cron.example
```

### Example setup
Open crontab:
```bash
crontab -e
```

Then add rules similar to:
```cron
*/5 * * * * cd /ABS/PATH/TO/Silver\ Tier && uv run orchestrator.py --project-root . --once >> AI_Employee_Vault/Logs/cron_orchestrator.log 2>&1
0 9 * * * cd /ABS/PATH/TO/Silver\ Tier && ./daily_briefing.sh >> AI_Employee_Vault/Logs/cron_daily.log 2>&1
```

## Recommended Daily Operation
### Option A. Run everything together
```bash
uv run main.py
```

### Option B. Run services separately
Terminal 1:
```bash
uv run python watchers/GmailWatcher.py --vault AI_Employee_Vault --interval 120
```

Terminal 2:
```bash
uv run python watchers/WhatsAppWatcher.py --vault AI_Employee_Vault --interval 60 --require-keywords
```

Terminal 3:
```bash
uv run python watchers/filesystem_watcher.py --vault AI_Employee_Vault
```

Terminal 4:
```bash
uv run orchestrator.py --project-root .
```

Terminal 5:
```bash
uv run main.py --run-hitl
```

## Troubleshooting
### Gmail watcher says `credentials.json not found`
Put OAuth credentials here:
```text
AI_Employee_Vault/credentials.json
```

### Gmail login loop or token issue
Delete:
```text
AI_Employee_Vault/token.json
```

Then run Gmail watcher again and login fresh.

### WhatsApp keeps asking for QR
Delete or reset:
```text
whatsapp_session/
```

Then run watcher again and scan QR once more.

### LinkedIn publish fails with security checkpoint
This usually means LinkedIn wants manual verification.
Use:
- `LINKEDIN_HEADLESS=false`
- log in manually once
- retry after account verification

### MCP email send fails
Check:
- SMTP username
- SMTP password or app password
- `EMAIL_FROM`
- internet connectivity

### Nothing is happening in `Needs_Action/`
Check:
- watcher is actually running
- correct vault path is being used
- dependencies are installed with `uv sync`

## Useful Paths
- `AI_Employee_Vault/Dashboard.md`
- `AI_Employee_Vault/Needs_Action/`
- `AI_Employee_Vault/Plans/`
- `AI_Employee_Vault/Pending_Approval/`
- `AI_Employee_Vault/Approved/`
- `AI_Employee_Vault/Rejected/`
- `AI_Employee_Vault/Logs/`

## Summary
If you only want the shortest path:

1. Run `uv sync`
2. Run `uv run playwright install chromium`
3. Add `.env`
4. Put Gmail OAuth file in `AI_Employee_Vault/credentials.json`
5. Run `uv run main.py`
6. Scan WhatsApp QR on first run
7. Review files in `Pending_Approval/`
8. Move approved files to `Approved/`

Silver Tier in this repo is watcher-driven, approval-gated, and skill-based.
