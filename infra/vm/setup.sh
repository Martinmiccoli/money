#!/usr/bin/env bash
# Installazione della VM (Ubuntu 22.04/24.04, ARM o x86). Da lanciare UNA volta sulla VM:
#   curl -fsSL https://raw.githubusercontent.com/Martinmiccoli/money/dev/infra/vm/setup.sh | bash
# Idempotente: si può rilanciare. Non apre porte: l'accesso remoto passa da Tailscale.
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/Martinmiccoli/money.git}"
DIR="$HOME/money"

echo "▶ pacchetti di sistema"
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl git age cron tzdata >/dev/null
sudo timedatectl set-timezone Europe/Rome

if ! command -v docker >/dev/null; then
  echo "▶ Docker"
  curl -fsSL https://get.docker.com | sudo sh >/dev/null
  sudo usermod -aG docker "$USER"
  echo "  (Docker installato: esci e rientra via SSH, poi rilancia questo script)"
  exit 0
fi

echo "▶ codice"
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull --ff-only; else git clone -q -b dev "$REPO_URL" "$DIR"; fi
cd "$DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "  ⚠️  Compila $DIR/.env (copia i valori dal Mac: password DB, chiavi Alpaca Paper, Telegram,"
  echo "     SEC_CONTACT, AGE_RECIPIENT, HEALTHCHECK_URL) e rilancia lo script."
  exit 0
fi

echo "▶ immagine e servizi (la prima compilazione richiede ~10-15 minuti su ARM)"
docker compose -f infra/prod/docker-compose.yml --env-file .env up -d --build --wait
docker compose -f infra/prod/docker-compose.yml --env-file .env run --rm -T app research/.venv/bin/money db migrate

echo "▶ cron (Europe/Rome)"
CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "# money:" > "$CRON" || true
cat >> "$CRON" <<CRONTAB
5 9 * * 1-5 $DIR/infra/prod/run-day.sh # money: paper trading
30 2 * * * COMPOSE_FILE=$DIR/infra/prod/docker-compose.yml $DIR/infra/backup/backup.sh >> $DIR/data/logs/backup.log 2>&1 # money: backup
30 3 1 * * COMPOSE_FILE=$DIR/infra/prod/docker-compose.yml $DIR/infra/backup/restore-test.sh >> $DIR/data/logs/backup.log 2>&1 # money: prova di ripristino
CRONTAB
crontab "$CRON" && rm "$CRON"

if ! command -v tailscale >/dev/null; then
  echo "▶ Tailscale (accesso privato dai tuoi dispositivi, nessuna porta aperta)"
  curl -fsSL https://tailscale.com/install.sh | sh >/dev/null
fi
echo
echo "✅ Fatto. Ultimi passi manuali:"
echo "   1. sudo tailscale up            (apri il link e accedi con il tuo account Tailscale)"
echo "   2. sudo tailscale serve --bg 8787   (webapp su https://<nome-vm>.<tailnet>.ts.net, solo per te)"
echo "   3. per la prova di ripristino copia la chiave privata age in ~/.config/money/age.key (chmod 600)"
