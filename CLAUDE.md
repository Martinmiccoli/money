# CLAUDE.md — progetto money

Sistema di trading personale: 50 € iniziali, crescita realistica, prima paper trading e poi soldi veri **solo dopo la validazione**.
Utente: tecnico ma non sviluppatore. Il codice lo scrive Claude, spiegando le scelte in italiano.

## Documenti da leggere prima di lavorare
- `docs/00-requisiti.md`: obiettivi e vincoli
- `docs/01-raccolta/00-sintesi.md`: evidenze della Fase 1 e decisioni prese
- `docs/02-progettazione/`: architettura, guardrails, validazione, ADR

## Regole non negoziabili
1. **Mai indebolire un guardrail** (`config/guardrails.toml`, `engine/crates/money-core`) senza una richiesta esplicita dell'utente. In quel caso: commit dedicato con la motivazione.
2. **Mai attivare `hybrid`/`live`** senza un report di validazione superato (G-15). Mai piazzare ordini reali (G-17).
3. **Costi e tasse sempre inclusi** in backtest e metriche. Un risultato "lordo" va etichettato come tale.
4. **Anti look-ahead** (G-11): nei backtest si usano solo dati pubblicati prima della decisione.
5. **Registrare ogni esperimento** (G-12) e riportare anche i risultati negativi.
6. **Onestà sui rendimenti:** niente promesse. Quando un'aspettativa non è realistica, va detto.
7. **Segreti** solo in `.env` (ignorato da git) o nei secret di GitHub.

## Agente fiscale (ADR-004)
Quando l'utente chiede di fisco:
- usa `knowledge/fisco/` e i report deterministici del ledger, mai numeri calcolati "a mano";
- cita la fonte e la data di verifica di ogni regola; se la regola può essere cambiata, verifica sul web;
- chiudi sempre ricordando che serve la verifica di un commercialista prima di qualsiasi dichiarazione.

## Stack e comandi
- Rust (`engine/`): non è installato in locale, si usa Docker:
  `docker run --rm -v "$PWD":/w -w /w/engine -e CARGO_HOME=/w/.cache/cargo -e CARGO_TARGET_DIR=/w/.cache/target rust:1-slim cargo test`
- Python (`research/`): uv, Python 3.12
- TypeScript (`web/`): Node
- Branch di lavoro: `dev`. Commit in italiano.
