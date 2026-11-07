#!/usr/bin/env bash
# Giornata di paper trading (M6/M7). Lanciato da launchd (Mac) o da cron (VM, M9).
# Log in data/logs/paper.log (ignorato da git). Riepilogo e avvisi di guasto su Telegram, se configurato.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p "$REPO/data/logs"
LOG="$REPO/data/logs/paper.log"

notify_failure() {
  local tail_log
  tail_log="$(tail -n 15 "$LOG" 2>/dev/null | grep -v '^INFO' || true)"
  (cd "$REPO/research" && uv run money notify failure "$tail_log") >>"$LOG" 2>&1 || true
}
trap notify_failure ERR

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
  docker compose -f "$REPO/infra/docker-compose.yml" --env-file "$REPO/.env" up -d --wait >/dev/null
  cd "$REPO/research"
  uv run money paper run-day
  uv run money paper status
  uv run money notify daily
} >>"$LOG" 2>&1
