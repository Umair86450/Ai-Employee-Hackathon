#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_DIR="$PROJECT_ROOT/AI_Employee_Vault"
LOG_DIR="$VAULT_DIR/Logs"
mkdir -p "$LOG_DIR"

RUN_TS="$(date '+%Y-%m-%d %H:%M:%S')"
RUN_LOG="$LOG_DIR/$(date +%F)_ralph_loop.log"

exec >>"$RUN_LOG" 2>&1
echo "[$RUN_TS] Ralph loop started"

if command -v uv >/dev/null 2>&1; then
  RUNNER=(uv run python "$PROJECT_ROOT/ralph_loop.py")
else
  RUNNER=(python3 "$PROJECT_ROOT/ralph_loop.py")
fi

"${RUNNER[@]}" --project-root "$PROJECT_ROOT" "$@"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ralph loop completed"
