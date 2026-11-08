#!/usr/bin/env bash
# Backup notturno cifrato del database (3.3): pg_dump in formato custom (compresso) → age (chiave pubblica
# in AGE_RECIPIENT). Il formato custom serve a TimescaleDB per il ripristino (pre/post_restore).
# Funziona sul Mac (compose di sviluppo) e sulla VM (compose di produzione): COMPOSE_FILE seleziona quale.
# Copia remota facoltativa con rclone (RCLONE_REMOTE, es. "oci:money-backups"). Restano 14 copie locali.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
set -a; . "$REPO/.env"; set +a
: "${AGE_RECIPIENT:?AGE_RECIPIENT mancante in .env (chiave pubblica age, vedi infra/vm/README.md)}"
COMPOSE_FILE="${COMPOSE_FILE:-$REPO/infra/docker-compose.yml}"
OUT="$REPO/data/backups"
mkdir -p "$OUT"
FILE="$OUT/money-$(date +%Y%m%d-%H%M).dump.age"
docker compose -f "$COMPOSE_FILE" --env-file "$REPO/.env" exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --compress=9 --no-owner 2>/dev/null \
  | age -r "$AGE_RECIPIENT" > "$FILE.tmp"
mv "$FILE.tmp" "$FILE"
ls -1t "$OUT"/money-*.dump.age | tail -n +15 | while read -r old; do rm -- "$old"; done
if [ -n "${RCLONE_REMOTE:-}" ]; then rclone copy "$FILE" "$RCLONE_REMOTE" --quiet; fi
echo "backup: $FILE ($(du -h "$FILE" | cut -f1))"
