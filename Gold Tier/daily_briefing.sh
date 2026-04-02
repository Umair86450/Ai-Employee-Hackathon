#!/usr/bin/env bash
set -euo pipefail

# Silver Tier daily scheduler entrypoint.
# Runs update-dashboard skill, then conditionally triggers post-linkedin skill.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_DIR="$PROJECT_ROOT/AI_Employee_Vault"
LOG_DIR="$VAULT_DIR/Logs"
mkdir -p "$LOG_DIR"

RUN_TS="$(date '+%Y-%m-%d %H:%M:%S')"
RUN_LOG="$LOG_DIR/$(date +%F)_daily_briefing.log"

exec >>"$RUN_LOG" 2>&1
echo "[$RUN_TS] Silver Tier daily briefing started"

CODEX_BIN="${CODEX_BIN:-codex}"
CODEX_MODEL="${CODEX_MODEL:-}"
FORCE_LINKEDIN="${FORCE_LINKEDIN:-0}"

if ! command -v "$CODEX_BIN" >/dev/null 2>&1; then
  echo "ERROR: codex CLI not found in PATH."
  exit 127
fi

cd "$PROJECT_ROOT"

CODEX_ARGS=(exec --full-auto --cd "$PROJECT_ROOT")
if [[ -n "$CODEX_MODEL" ]]; then
  CODEX_ARGS+=(--model "$CODEX_MODEL")
fi

run_codex() {
  local prompt="$1"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] codex exec: ${prompt:0:80}..."
  "$CODEX_BIN" "${CODEX_ARGS[@]}" "$prompt"
}

# 1) Always refresh dashboard via skill.
run_codex "Use .agents/skills/update-dashboard/SKILL_update_dashboard.md workflow now. Read Company_Handbook.md, refresh AI_Employee_Vault/Dashboard.md, and append today's log entry. Keep output short."

# 2) Trigger LinkedIn skill only if needed.
# Needed rule:
# - Trigger when FORCE_LINKEDIN=1, OR
# - Needs_Action has files AND no linkedin approval request exists for today.
TODAY="$(date +%F)"
NEEDS_ACTION_COUNT="$(find "$VAULT_DIR/Needs_Action" -maxdepth 1 -type f ! -name '.gitkeep' | wc -l | tr -d ' ')"
LINKEDIN_APPROVAL_TODAY_COUNT="$(
  {
    find "$VAULT_DIR/Pending_Approval" -maxdepth 1 -type f -name "APPROVAL_${TODAY}_*linkedin_post*.md" 2>/dev/null || true
    find "$VAULT_DIR/Approved" -maxdepth 1 -type f -name "APPROVAL_${TODAY}_*linkedin_post*.md" 2>/dev/null || true
    find "$VAULT_DIR/Rejected" -maxdepth 1 -type f -name "APPROVAL_${TODAY}_*linkedin_post*.md" 2>/dev/null || true
  } | wc -l | tr -d ' '
)"

echo "Needs_Action=$NEEDS_ACTION_COUNT, LinkedInRequestsToday=$LINKEDIN_APPROVAL_TODAY_COUNT, FORCE_LINKEDIN=$FORCE_LINKEDIN"

if [[ "$FORCE_LINKEDIN" == "1" || ( "$NEEDS_ACTION_COUNT" -gt 0 && "$LINKEDIN_APPROVAL_TODAY_COUNT" -eq 0 ) ]]; then
  run_codex "Use .agents/skills/post-linkedin/SKILL.md workflow. Create a sales-focused LinkedIn draft for Digital AI Employee (8-hour human vs 24/7 AI), generate image prompt, and create approval request only. Do not publish."
else
  echo "Skipping LinkedIn trigger (not needed by rule)."
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Silver Tier daily briefing completed"
