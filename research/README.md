# research/ — Python (uv, 3.12)
Ingest, segnali, combiner ML e backtest. Vedi [architettura](../docs/02-progettazione/architettura.md).

## Avvio rapido (M1)
```bash
cp ../.env.example ../.env          # compila password DB e chiavi Alpaca Paper
docker compose -f ../infra/docker-compose.yml --env-file ../.env up -d
uv run money ingest all             # migrazioni + universo + cambi BCE + prezzi
uv run money status                 # copertura dei dati
uv run money chart                  # grafico in reports/charts/
```
Senza chiavi Alpaca vengono scaricate solo le crypto; azioni ed ETF richiedono le chiavi del conto paper.

## Moduli
| Modulo | Contenuto |
|---|---|
| `config.py` | `.env` e `config/universe.toml` (con validazione degli ISIN) |
| `db.py` | connessione, migrazioni (`infra/migrations/`), sync dell'universo, registro delle esecuzioni |
| `ingest/ecb.py` | cambi di riferimento BCE |
| `ingest/alpaca.py` | client Market Data Alpaca (paginazione, retry 429, fallback SIP→IEX) |
| `ingest/prices.py` | barre giornaliere raw + rettificate dei proxy, ingest incrementale |
