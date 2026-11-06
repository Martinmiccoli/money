# money

Sistema personale di investimento quantitativo: segnali da insider, superinvestor, fattori e sentiment; guardrails di rischio in Rust; paper trading prima dei soldi veri; agente fiscale per il regime italiano.

> ⚠️ Progetto personale e sperimentale. Non è una consulenza finanziaria né fiscale. Investire comporta il rischio di perdere il capitale.

## Stato
| Fase | Stato |
|---|---|
| 1. Raccolta informazioni | ✅ [sintesi](docs/01-raccolta/00-sintesi.md) |
| 2. Progettazione e guardrails | ✅ [architettura](docs/02-progettazione/architettura.md) · [guardrails](docs/02-progettazione/guardrails.md) · [validazione](docs/02-progettazione/validazione.md) |
| 3. System design puntuale | ⏳ |
| 4. Linguaggi | ✅ [ADR-001](docs/02-progettazione/adr/001-stack-linguaggi.md) |
| 5. Sviluppo | ⏳ (guardrails già implementati e testati in `engine/crates/money-core`) |
| 6. Paper → validazione → live | ⏳ |

## Struttura
`engine/` Rust · `research/` Python · `web/` TypeScript · `config/` guardrails · `knowledge/fisco/` · `infra/` · `docs/`
