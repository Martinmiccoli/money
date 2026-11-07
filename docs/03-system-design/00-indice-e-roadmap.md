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
| **M3** ✅ | Simulatore + metriche | backtest event-driven, DSR, PBO, registro G-12, report di validazione | primo report: **benchmark piano di accumulo** |
| **M4** ✅ (esito negativo) | Prime strategie | S3 trend + S4 rotazione + S8 regime (solo ETF: i dati più semplici) | Gate 0 sulle strategie ETF |
| **M5** | Insider | ingest Form 4 + S1 + filtri | Gate 0 su S1 |
| **M6** ✅ (avviato il 2026-11-07) | Paper trading | `money-engine` + SimBroker + AlpacaPaper, scheduler, heartbeat | **inizio del Gate 1** (3-6 mesi) |
| **M7** ✅ | Webapp e notifiche | API Hono, PWA, bot Telegram, flusso proposte | proposte sul telefono |
| **M8** ✅ (esito negativo) | Sentiment | GDELT, Wikipedia, FinBERT, S6 (veto e feature), laboratorio crypto | Gate 0 sui filtri |
| **M9** | Deploy | VM Oracle, Cloudflare Tunnel, backup, watchdog | sistema acceso 24/7 |
| **M10** | Agente fiscale | `knowledge/fisco/`, report annuale, riconciliazione dell'export Trade Republic | primo report fiscale |
| M11 | Estensioni | S2 13F, S5 v2, S7 Congresso, combiner ML | da valutare con i dati |

**Il paper trading (M6) parte il prima possibile,** perché il Gate 1 richiede almeno 3 mesi di calendario: i milestone successivi si sviluppano mentre il paper gira.

## Esito della M4 (2026-11-07) — risultato negativo, registrato (G-12, regola 5)
Report: [`reports/validation/2026-11-07-m4-strategie-etf.md`](../../reports/validation/2026-11-07-m4-strategie-etf.md). Periodo di ricerca 2017 → agosto 2024; l'hold-out **non è stato aperto**, perché nessuna variante supera il Gate 0 nemmeno in-sample.
- **50 € e 1.000 €:** le strategie S3, S4 e S3+S4+S8 **non riescono a operare**. Con 1 € di commissione, G-05 e G-06 bloccano gli ordini piccoli: il rendimento atteso di un ribilanciamento non copre il costo.
- **10.000 € (diagnostica):** operano, ma rendono 1,8-3,1% l'anno netto contro il 7,6% del piano di accumulo, con drawdown molto più bassi (−8% / −19% contro −34%). Lo Sharpe è simile o inferiore a quello del benchmark (0,30-0,50 contro 0,46).
- **Limite del test:** i dati partono dal 2016, quindi la stima dell'edge (point-in-time) si forma lentamente e le strategie restano in liquidità per gran parte del 2017-2019.
- **Conseguenza:** con il capitale attuale, il satellite ETF tattico non è attivabile. Resta valido il core con il piano di accumulo (3.2, "sblocco per capitale").

## Esito della M7 (2026-11-07)
- **Webapp** (Hono + React, PWA, solo `127.0.0.1`): conti, andamento, posizioni, ordini con l'ombra Alpaca, ledger leggibile, guardrails e pulsante di ripartenza dopo il soft stop (`money-engine resume`).
- **Telegram:** riepilogo dopo ogni giornata, avviso immediato se la giornata fallisce, **anteprima** delle proposte hybrid nel formato del 3.5 (prezzo massimo, scadenza, motivo, rendimento atteso).
- **Non ancora:** il flusso di conferma reale (✅ Eseguito / ⏭ Salta con registrazione del fill) serve solo in modalità hybrid, che richiede la validazione (G-15). Verrà implementato insieme all'adapter `ManualTap`. Lo stesso vale per Web Push: Telegram basta.

## Esito della M8 (2026-11-07) — sentiment: risultato negativo, registrato (G-12)
Report: [`reports/validation/2026-11-07-m8-sentiment.md`](../../reports/validation/2026-11-07-m8-sentiment.md). Periodo di ricerca da marzo 2018 ad agosto 2024; hold-out intatto.
- **Fear & Greed contrarian sulla quota bitcoin:** a 1.000 € e 10.000 € **rende meno che tenere sempre il bitcoin** (6,7-9,6% contro 10,5-11,6% annuo). Il segnale non aggiunge valore.
- **Narrazione di crisi (GDELT):** **fortemente negativa** (da −1,9% a 0% annuo contro +7,7% dell'ETF tenuto). Il volume di notizie su recessione e crolli tocca il massimo *vicino ai minimi* (marzo 2020): la strategia esce al momento peggiore e perde il rimbalzo.
- **Nota sul bitcoin "sempre":** 85% ETF + 14% BTC ha reso circa 2-3 punti l'anno più del solo ETF, ma con meno di 30 operazioni e DSR sotto il 95%. Soprattutto, **scegliere il bitcoin oggi, sapendo come è andato dal 2018 al 2024, è senno di poi**: non è una prova di valore futuro.
- **Rimandati a S1 (M5):** FinBERT sul tono delle notizie e veto anti-hype sulle azioni. Wikipedia richiede un contatto per la policy Wikimedia (`WIKIMEDIA_CONTACT`).
- **Bug trovati e corretti durante la M8:** riserva di liquidità negli acquisti (influiva anche sulla M4: S3 a 10.000 € passa da 2,8% a 4,8%, sempre sotto il benchmark), minimo del piano di accumulo, compatibilità degli stati salvati dal paper.
