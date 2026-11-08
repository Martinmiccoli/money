#!/usr/bin/env bash
# Ripristina un backup nel database di un compose (es. migrazione Mac → VM). Il database di destinazione
# deve essere VUOTO: lo script si rifiuta di sovrascrivere un ledger esistente (G-16).
#   COMPOSE_FILE=infra/prod/docker-compose.yml ./infra/backup/restore.sh data/backups/money-AAAAMMGG-HHMM.dump.age
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
set -a; . "$REPO/.env"; set +a
FILE="${1:?uso: restore.sh <backup.dump.age>}"
KEY="${AGE_IDENTITY_FILE:-$HOME/.config/money/age.key}"
COMPOSE=(docker compose -f "${COMPOSE_FILE:-$REPO/infra/docker-compose.yml}" --env-file "$REPO/.env")
psqlc() { "${COMPOSE[@]}" exec -T db psql -tA -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"; }
if [ "$(psqlc -c "SELECT to_regclass('ledger.event') IS NOT NULL")" = "t" ] && \
   [ "$(psqlc -c "SELECT count(*) FROM ledger.event")" != "0" ]; then
  echo "il database di destinazione contiene già un ledger: ripristino rifiutato"; exit 1
fi
psqlc -c "CREATE EXTENSION IF NOT EXISTS timescaledb; SELECT timescaledb_pre_restore();" >/dev/null
age -d -i "$KEY" "$FILE" | "${COMPOSE[@]}" exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --no-owner --disable-triggers --clean --if-exists 2>/dev/null || true
psqlc -c "SELECT timescaledb_post_restore();" >/dev/null
echo "ripristinato: ledger $(psqlc -c "SELECT count(*) FROM ledger.event") eventi, $(psqlc -c "SELECT count(*) FROM market.bar_1d") barre"
