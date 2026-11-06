# research/ — Python (uv, 3.12)
Ingest, segnali, combiner ML e backtest. Vedi [architettura](../docs/02-progettazione/architettura.md).

## Avvio rapido (M1)
```bash
cp ../.env.example ../.env          # compila password DB e chiavi Alpaca Paper
docker compose -f ../infra/docker-compose.yml --env-file ../.env up -d
uv run money ingest all             # migrazioni + universo + cambi BCE + prezzi
uv run money status                 # copertura dei dati
uv run money chart                  # grafico in reports/charts/
uv run money backtest benchmark     # M3: report del benchmark in reports/validation/
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

## Binding `money_py` (M2)
Costi, ledger e fisco del backtest arrivano da `money-core` (Rust) tramite PyO3, così il backtest paga gli stessi costi e le stesse tasse del live.
Gli importi passano come stringhe decimali (`decimal.Decimal`), mai come float. I test `tests/test_money_py.py` vengono saltati se il binding non è installato.

## Backtest (M3) — `money_research.backtest`
| Modulo | Contenuto |
|---|---|
| `data.py` | dati point-in-time: la strategia vede solo `available_at` < ora della decisione (G-11) |
| `simulator.py` | loop giornaliero event-driven: guardrails, costi, ledger e fisco da `money_py` |
| `strategies.py` | `SavingsPlan` (benchmark); le strategie vere implementano lo stesso protocollo |
| `metrics.py` | TWR, Sharpe (€STR), Sortino, drawdown, PSR, **Deflated Sharpe**, **PBO** (CSCV) |
| `registry.py` | registro G-12 (`research.experiment`, append-only) e accessi all'hold-out |
| `report.py`, `run.py` | report di validazione Markdown + grafico + sha256 |

Parametri fissati a priori in `config/validation.toml` (hold-out dal 2024-09-02).
