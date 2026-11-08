#!/usr/bin/env bash
# Giornata di paper trading sulla VM (cron, lun-ven 09:05 Europe/Rome). Tutto gira nel container "app".
# Al termine: ping al watchdog (HEALTHCHECK_URL, es. healthchecks.io) se configurato.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE=(docker compose -f "$REPO/infra/prod/docker-compose.yml" --env-file "$REPO/.env")
LOG="$REPO/data/logs/paper.log"
mkdir -p "$REPO/data/logs"
set -a; . "$REPO/.env"; set +a
money() { "${COMPOSE[@]}" run --rm -T app research/.venv/bin/money "$@"; }

on_error() {
  money notify failure "$(tail -n 15 "$LOG" | grep -v '^INFO' || true)" >>"$LOG" 2>&1 || true
  [ -n "${HEALTHCHECK_URL:-}" ] && curl -fsS -m 10 "$HEALTHCHECK_URL/fail" >/dev/null || true
}
trap on_error ERR

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
  "${COMPOSE[@]}" up -d --wait db app >/dev/null
  money paper run-day
  money paper status
  money notify daily
} >>"$LOG" 2>&1

[ -n "${HEALTHCHECK_URL:-}" ] && curl -fsS -m 10 "$HEALTHCHECK_URL" >/dev/null || true
