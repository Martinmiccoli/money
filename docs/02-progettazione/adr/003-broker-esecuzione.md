# ADR-003 — Broker ed esecuzione
**Stato:** accettato (2026-11-06), da rivedere al Gate 2

## Decisione
| Fase | Broker | Modalità | Regime fiscale |
|---|---|---|---|
| Ricerca | — | simulatore `money-core` | modello IT simulato |
| Paper | SimBroker + **Alpaca Paper** | automatica | nessuno (soldi finti) |
| Live con 50 € | **Trade Republic** | **hybrid:** proposta con prezzo limite e scadenza → notifica → tap; stop-loss sul broker; piano di accumulo ETF automatico | **amministrato** (zero adempimenti) |
| Live oltre ~1.000 € (opzionale) | Saxo OpenAPI (amministrato, da confermare) oppure IBKR/Alpaca | automazione totale | amministrato oppure dichiarativo con quadri preparati dall'agente fiscale |

La scelta definitiva tra hybrid e automazione totale si fa dopo il paper trading, con i dati reali.

## Esclusi
- Le API non ufficiali di Trade Republic e DEGIRO (es. `pytr`): violano i ToS e possono portare alla chiusura del conto.
- eToro CopyTrader: richiede almeno 200 $.
- Crypto spot nel live: aliquota al 33%, nessun sostituto d'imposta. Nel live si usano gli ETP.
