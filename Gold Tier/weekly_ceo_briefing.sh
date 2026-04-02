#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_DIR="$PROJECT_ROOT/AI_Employee_Vault"
LOG_DIR="$VAULT_DIR/Logs"
mkdir -p "$LOG_DIR"

RUN_TS="$(date '+%Y-%m-%d %H:%M:%S')"
RUN_LOG="$LOG_DIR/$(date +%F)_weekly_ceo_briefing.log"

exec >>"$RUN_LOG" 2>&1
echo "[$RUN_TS] Weekly CEO briefing started"

CODEX_BIN="${CODEX_BIN:-codex}"
CODEX_MODEL="${CODEX_MODEL:-}"

if ! command -v "$CODEX_BIN" >/dev/null 2>&1; then
  echo "ERROR: codex CLI not found in PATH."
  exit 127
fi

cd "$PROJECT_ROOT"

CODEX_ARGS=(exec --full-auto --cd "$PROJECT_ROOT")
if [[ -n "$CODEX_MODEL" ]]; then
  CODEX_ARGS+=(--model "$CODEX_MODEL")
fi

PROMPT="Use skill file \`.agents/skills/weekly-ceo-briefing/SKILL.md\` and follow it exactly. Generate the weekly CEO briefing now using odoo_mcp plus AI_Employee_Vault context, save it to AI_Employee_Vault/Briefings/<YYYY-MM-DD>_CEO_Briefing.md, and update dashboard/logs."

echo "[$(date '+%Y-%m-%d %H:%M:%S')] codex exec: weekly CEO briefing..."
"$CODEX_BIN" "${CODEX_ARGS[@]}" "$PROMPT"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Weekly CEO briefing completed"
