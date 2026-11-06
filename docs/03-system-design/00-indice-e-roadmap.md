# Fase 3 — System design: indice e roadmap di sviluppo

| # | Documento | Contenuto |
|---|---|---|
| 3.1 | [Segnali](01-segnali.md) | S1 insider · S2 13F · S3 trend · S4 rotazione · S5 fattori · S6 sentiment · S7 Congresso · S8 regime · combiner ML |
| 3.2 | [Portafoglio e rischio](02-portafoglio-e-rischio.md) | core/satellite, sblocco per capitale, sizing, banda di non-trading, stop |
| 3.3 | [Dati e ledger](03-dati-e-ledger.md) | schema point-in-time, ledger append-only a catena di hash |
| 3.4 | [Costi e fisco](04-costi-e-fisco.md) | profilo costi Trade Republic, zainetto, RD vs RC, report fiscale |
| 3.5 | [Esecuzione](05-esecuzione-hybrid.md) | adapter, ciclo di vita della proposta, notifiche, riconciliazione |
| 3.6 | [Backtest e metriche](06-backtest-e-metriche.md) | simulatore, bias, DSR, PBO, registro esperimenti |

## Roadmap della Fase 5 (sviluppo), in ordine di valore
Ogni milestone finisce con test verdi e una demo funzionante.

| M | Obiettivo | Contenuto | Risultato visibile |
|---|---|---|---|
| **M1** ✅ | Dati | Docker Compose (Postgres + Timescale), schema 3.3, ingest dei prezzi (Alpaca, cambio BCE, ETF UCITS) | DB popolato, grafici dei prezzi |
| **M2** ✅ | Cuore contabile | `money-core`: costi, ledger (decimal, catena di hash), fisco/zainetto; binding PyO3 | test sul fisco con casi reali |
| **M3** | Simulatore + metriche | backtest event-driven, DSR, PBO, registro G-12, report di validazione | primo report: **benchmark piano di accumulo** |
| **M4** | Prime strategie | S3 trend + S4 rotazione + S8 regime (solo ETF: i dati più semplici) | Gate 0 sulle strategie ETF |
| **M5** | Insider | ingest Form 4 + S1 + filtri | Gate 0 su S1 |
| **M6** | Paper trading | `money-engine` + SimBroker + AlpacaPaper, scheduler, heartbeat | **inizio del Gate 1** (3-6 mesi) |
| **M7** | Webapp e notifiche | API Hono, PWA, bot Telegram, flusso proposte | proposte sul telefono |
| **M8** | Sentiment | GDELT, Wikipedia, FinBERT, S6 (veto e feature), laboratorio crypto | Gate 0 sui filtri |
| **M9** | Deploy | VM Oracle, Cloudflare Tunnel, backup, watchdog | sistema acceso 24/7 |
| **M10** | Agente fiscale | `knowledge/fisco/`, report annuale, riconciliazione dell'export Trade Republic | primo report fiscale |
| M11 | Estensioni | S2 13F, S5 v2, S7 Congresso, combiner ML | da valutare con i dati |

**Il paper trading (M6) parte il prima possibile,** perché il Gate 1 richiede almeno 3 mesi di calendario: i milestone successivi si sviluppano mentre il paper gira.
