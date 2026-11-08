#!/usr/bin/env bash
# Prova di ripristino (mensile): decifra l'ultimo backup in un Postgres usa e getta e confronta i conteggi
# del ledger con il database vivo. Un backup mai ripristinato non è un backup.
# Serve la chiave privata age in AGE_IDENTITY_FILE (default ~/.config/money/age.key), MAI nel repo.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
set -a; . "$REPO/.env"; set +a
KEY="${AGE_IDENTITY_FILE:-$HOME/.config/money/age.key}"
COMPOSE_FILE="${COMPOSE_FILE:-$REPO/infra/docker-compose.yml}"
LAST="$(ls -1t "$REPO"/data/backups/money-*.dump.age | head -1)"
NAME="money-restore-test-$$"
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT
docker run -d --name "$NAME" -e POSTGRES_PASSWORD=test timescale/timescaledb:2.17.2-pg16 >/dev/null
until docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
sleep 2
# Procedura TimescaleDB: estensione, pre_restore, pg_restore (trigger disattivati: l'ordine delle righe nel
# dump non è garantito e il trigger della catena le rifiuterebbe; la catena si verifica dopo), post_restore.
docker exec "$NAME" psql -q -U postgres -c "CREATE DATABASE money" >/dev/null
docker exec "$NAME" psql -q -U postgres -d money -c "CREATE EXTENSION IF NOT EXISTS timescaledb; SELECT timescaledb_pre_restore();" >/dev/null
age -d -i "$KEY" "$LAST" | docker exec -i "$NAME" pg_restore -U postgres -d money --no-owner --disable-triggers 2>/dev/null || true
docker exec "$NAME" psql -q -U postgres -d money -c "SELECT timescaledb_post_restore();" >/dev/null
q="SELECT count(*) || '/' || coalesce(max(seq),0) FROM ledger.event"
restored="$(docker exec "$NAME" psql -tA -U postgres -d money -c "$q")"
bars="$(docker exec "$NAME" psql -tA -U postgres -d money -c "SELECT count(*) FROM market.bar_1d")"
echo "barre di prezzo ripristinate: $bars"
live="$(docker compose -f "$COMPOSE_FILE" --env-file "$REPO/.env" exec -T db psql -tA -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$q")"
echo "ripristino di $(basename "$LAST"): ledger $restored (vivo: $live)"
[ -n "$restored" ] && [ "$restored" = "$live" ] && [ "${bars:-0}" -gt 0 ] || { echo "RIPRISTINO NON COERENTE"; exit 1; }
echo "ripristino OK"
