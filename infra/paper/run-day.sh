#!/usr/bin/env bash
# Giornata di paper trading (M6). Lanciato da launchd (Mac) o da cron (VM, M9).
# Log in data/logs/paper.log (ignorato da git).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p "$REPO/data/logs"
LOG="$REPO/data/logs/paper.log"
{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
  docker compose -f "$REPO/infra/docker-compose.yml" --env-file "$REPO/.env" up -d --wait >/dev/null
  cd "$REPO/research"
  uv run money paper run-day
  uv run money paper status
} >>"$LOG" 2>&1
