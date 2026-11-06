# ADR-004 — Agente fiscale
**Stato:** accettato (2026-11-06)

## Decisione
- L'agente fiscale è **Claude Code**, invocato dall'utente nel repo.
- **Knowledge base:** `knowledge/fisco/*.md`. Ogni regola riporta fonte (link normativo o Agenzia delle Entrate), data di entrata in vigore e data dell'ultima verifica.
- **Calcoli:** solo deterministici, in `money-core::tax`, sul ledger: zainetto delle minusvalenze per anno di scadenza, ETF come redditi di capitale (non compensabili), Tobin tax, bollo, ritenute sui dividendi USA.
- Claude legge i report, li spiega, segnala anomalie e novità normative. Non inventa numeri e non sostituisce legalmente un commercialista.
- In regime amministrato i report servono come **controllo** di ciò che trattiene il broker. In regime dichiarativo, l'agente prepara la bozza dei quadri da far verificare.

## Manutenzione
- Revisione della knowledge base a ogni legge di bilancio (gennaio) e prima del 730.
