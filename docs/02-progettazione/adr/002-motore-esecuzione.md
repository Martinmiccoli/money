# ADR-002 — Motore: engine Rust nostro, non NautilusTrader
**Stato:** accettato (2026-11-06)

## Contesto
NautilusTrader (core Rust, 31k stelle, LGPL) era il candidato della Fase 1. Però:
- **non ha un adapter per Alpaca** (il nostro broker paper) e ovviamente non ne ha uno per un'esecuzione "manuale con tap" su Trade Republic;
- è progettato per il trading event-driven e ad alta frequenza, mentre noi operiamo da giornaliero a mensile con poche decine di ordini al mese;
- i requisiti più critici (fisco italiano, guardrails specifici, flusso hybrid con proposte e scadenze) andrebbero comunque scritti da noi.

## Decisione
- **Engine Rust leggero e nostro** (`money-core` + `money-engine`), con adapter di esecuzione intercambiabili (`SimBroker`, `AlpacaPaper`, `ManualTap`, in futuro `Saxo`/`IBKR`).
- **vectorbt** (Python) per la ricerca veloce e gli sweep di parametri. Il backtest di validazione finale passa però dal nostro simulatore, che usa `money-core`.
- **Riusati:** edgartools (SEC), ccxt (crypto), FinBERT (sentiment locale), client REST di Alpaca.
- Se in futuro serve un motore event-driven completo (es. per IBKR), rivalutiamo NautilusTrader.

## Conseguenze
- Più codice nostro, ma piccolo e testabile. Il cuore (guardrails) viene scritto per primo, con test.
