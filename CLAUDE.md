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
- Rust (`engine/`): installato in locale con rustup (`~/.cargo/bin`). `cd engine && cargo test` · `cargo clippy --workspace --all-targets -- -D warnings` · `cargo fmt`
- Binding `money_py` (PyO3): dipendenza di `research/`, `uv sync` lo ricompila quando cambia il codice Rust
- Python (`research/`): uv, Python 3.12. `cd research && uv run pytest` (con `TEST_DATABASE_URL` girano anche i test sul DB)
- DB locale: `docker compose -f infra/docker-compose.yml --env-file .env up -d` (Postgres + Timescale su 127.0.0.1:5433)
- Dati: `cd research && uv run money ingest all` · `uv run money status` · `uv run money chart`
- Backtest: `uv run money backtest benchmark` · `uv run money backtest m4` (ogni esecuzione finisce nel registro G-12)
- Paper trading (M6): `uv run money paper run-day` · `uv run money paper status` · motore: `engine/target/release/money-engine settle|execute|status` · automatico: `infra/paper/run-day.sh` (launchd)
- TypeScript (`web/`): Node
- Branch di lavoro: `dev`. Commit in italiano.
