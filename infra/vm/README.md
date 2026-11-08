# M9 — Il sistema su una VM sempre accesa

Obiettivo: il paper trading gira ogni giorno anche a Mac spento. Costo: **0 €** (Oracle Cloud Always Free + Tailscale personale).

## 1. Crea la VM (tu, ~20 minuti)
1. Registrati su **Oracle Cloud** (cloud.oracle.com → "Start for free"). La carta di credito serve solo come verifica: le risorse **Always Free** non costano nulla. Scegli una *home region* vicina (es. Milano o Francoforte): non si cambia più.
2. *Compute → Instances → Create instance*:
   - Image: **Ubuntu 24.04** · Shape: **Ampere A1 (VM.Standard.A1.Flex)**, 2 OCPU e 12 GB (dentro l'Always Free).
   - SSH: carica la tua chiave pubblica (`~/.ssh/id_ed25519.pub`; se non ce l'hai: `ssh-keygen -t ed25519`).
   - Rete: lascia la VCN predefinita. **Non aprire altre porte** oltre alla 22 (SSH).
3. ⚠️ Oracle può recuperare le istanze Always Free "inattive". Per evitarlo puoi passare l'account a *Pay As You Go*: le risorse Always Free restano gratuite. È facoltativo; il backup notturno protegge comunque i dati.
4. Dammi l'IP pubblico: mi collegherò con `ssh ubuntu@<IP>`.

## 2. Installa (io, oppure tu con un comando)
```bash
ssh ubuntu@<IP>
curl -fsSL https://raw.githubusercontent.com/Martinmiccoli/money/dev/infra/vm/setup.sh | bash   # Docker → esci/rientra → rilancia
nano ~/money/.env                                                                         # copia i valori dal Mac
~/money/infra/vm/setup.sh                                                                 # build, servizi, cron, Tailscale
```
Lo script installa Docker, `age`, il codice, costruisce l'immagine (motore Rust, money_py, CLI, webapp) e programma:

| Quando (Europe/Rome) | Cosa |
|---|---|
| lun-ven 09:05 | giornata di paper trading + riepilogo Telegram (`infra/prod/run-day.sh`) |
| ogni notte 02:30 | backup cifrato con `age` (`infra/backup/backup.sh`), 14 copie, copia remota facoltativa con rclone |
| il 1° del mese 03:30 | prova di ripristino in un database usa e getta (`infra/backup/restore-test.sh`) |

## 3. Accesso dal telefono: Tailscale (gratuito, privato)
- Installa **Tailscale** sul telefono e sul Mac e accedi con lo stesso account.
- Sulla VM: `sudo tailscale up`, poi `sudo tailscale serve --bg 8787`.
- La webapp è su `https://<nome-vm>.<tailnet>.ts.net`, **visibile solo ai tuoi dispositivi**: nessuna porta aperta su internet.
- Perché non Cloudflare Tunnel (previsto nel design): richiede un dominio (~10 €/anno), fuori dal budget di 0 €. Resta disponibile nel compose (profilo `cloudflare`).

## 4. Watchdog
- **Telegram:** avviso immediato se la giornata fallisce (già attivo).
- **healthchecks.io** (gratuito): crea un check "money paper" con periodo 1 giorno e tolleranza 6 ore, collega l'integrazione Telegram, metti l'URL in `HEALTHCHECK_URL`. Se la VM si spegne o il cron non parte, l'avviso arriva da lì: un sistema morto non può avvisare da solo.

## 5. Migrazione dei dati dal Mac
```bash
# sul Mac
./infra/backup/backup.sh
scp data/backups/money-*.dump.age ubuntu@<IP>:~/money/data/backups/
scp ~/.config/money/age.key ubuntu@<IP>:~/.config/money/age.key     # chiave privata: solo via SSH
# sulla VM: ripristino nel database di produzione (procedura TimescaleDB: vedi restore-test.sh)
```
Dopo la migrazione **disattiva il job sul Mac** (`launchctl unload ~/Library/LaunchAgents/com.money.paper.plist`), altrimenti i due sistemi lavorerebbero sugli stessi conti in due database diversi.

## Sicurezza
- Segreti solo in `.env` (permessi 600) e nella chiave age, **mai** nell'immagine o nel repo (G-14). Il repository è pubblico.
- Database e webapp ascoltano solo su `127.0.0.1` della VM.
- La chiave privata age è anche la chiave dei tuoi backup: conservane una copia nel gestore di password.
