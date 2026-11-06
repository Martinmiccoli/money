# 11 — Interessi sulla liquidità
- **Ultima verifica:** 2026-11-07 · **Codice:** `Event::Interest`, `tax.rs` (operazione `Interest`)
- **Fonte:** [broker-e-fisco.md](../../docs/01-raccolta/broker-e-fisco.md) regola 13 (🟡); art. 44 TUIR → art. 46 nuovo TUIR (redditi di capitale); ritenuta del 26% (D.L. 66/2014).

- Gli interessi sulla liquidità sono **redditi di capitale** al 26%, trattenuti dal broker in amministrato. Non si compensano con lo zainetto. 🟡
- Nel backtest l'interesse è stimato con l'€STR quando è positivo: tra il 2016 e metà 2022 il tasso era negativo e Trade Republic non pagava interessi.
