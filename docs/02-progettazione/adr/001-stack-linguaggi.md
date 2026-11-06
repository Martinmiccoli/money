# ADR-001 — Stack: Rust + TypeScript + Python
**Stato:** accettato (2026-11-06) · copre la fase "scelta del linguaggio"

## Contesto
L'utente ha scelto Rust per il motore, TypeScript per webapp/API/orchestrazione e Python per ML/backtest. La Fase 1 ha confermato che l'ecosistema quant/ML vive in Python (pandas, scikit-learn, LightGBM, vectorbt, edgartools, FinBERT).

## Decisione
- **Rust:** `money-core` (guardrails, rischio, costi, fisco, ledger) e `money-engine` (esecuzione). Garantisce correttezza dei tipi, nessun errore nascosto a runtime e un singolo binario leggero sulla VM ARM.
- **Python (uv, 3.12):** ingest, segnali, combiner ML, backtest. Usa `money-core` via PyO3, così da avere un solo modello di costi, rischio e fisco.
- **TypeScript (Node, Hono + React/Vite):** API, webapp PWA, bot di notifica.

## Conseguenze
- Tre toolchain, quindi una CI unica che le testa tutte.
- Il confine tra linguaggi è **il database** (Postgres) più i binding PyO3. Niente microservizi che si chiamano a vicenda.
- La velocità di Rust non è il motivo principale (si opera da giornaliero a mensile): lo sono **sicurezza e correttezza** sul codice che tocca i soldi.
