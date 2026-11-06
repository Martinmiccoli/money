# 3.3 — Dati, database e ledger

## Principi
1. **Point-in-time:** ogni dato ha tre tempi:
   - `as_of`: a cosa si riferisce;
   - `available_at`: quando è diventato pubblico;
   - `ingested_at`: quando l'abbiamo scaricato.

   I backtest filtrano sempre su `available_at` (G-11). Le revisioni dei dati non sovrascrivono: aggiungono una nuova versione.
2. **Il ledger è la verità contabile:** posizioni, cassa, equity e tasse sono **proiezioni** calcolate dagli eventi, mai salvate come stato modificabile (G-16).
3. **Importi monetari in decimale esatto** nel ledger e nel fisco (`rust_decimal` in Rust, `Decimal`/NUMERIC in Postgres). `f64` va bene solo nei calcoli statistici e nei controlli di soglia.

## Schemi Postgres (+ TimescaleDB per le serie)
```
ref.instrument      (instrument_id, isin, figi, ticker, mic, asset_class, currency, name, tax_category, active_from, active_to)
ref.instrument_map  (instrument_id, source, source_symbol, valid_from, valid_to)      -- SEC/Alpaca/TR/OpenFIGI

market.bar_1d       (instrument_id, date, open, high, low, close, adj_close, volume, source, ingested_at)  -- hypertable
market.fx_1d        (pair, date, rate, source)                                         -- BCE
market.corporate_action (instrument_id, ex_date, kind, ratio, amount, available_at)

raw.form4           (accession_no, cik_issuer, cik_insider, role, tx_date, tx_code, shares, price, shares_after, is_10b5_1, accepted_at, ingested_at)
raw.f13f            (accession_no, cik_manager, period, cusip, shares, value_usd, filed_at)
raw.news            (id, source, url, published_at, ingested_at, title, tickers[], tone_finbert, gdelt_tone)
raw.attention       (instrument_id, date, wiki_views, gdelt_mentions)
raw.macro           (series_id, date, value, available_at, source)
raw.congress_ptr    (filing_id, member, role, tx_date, ticker, side, amount_range, published_at)

signals.signal      (signal_id, run_id, pillar, instrument_id, as_of, available_at, horizon_days, score, confidence, expected_edge_pct, explain)
signals.target      (run_id, sleeve, instrument_id, weight, as_of)
signals.run         (run_id, code_version, config_hash, started_at, finished_at, status)

research.experiment (experiment_id, created_at, code_version, config_json, data_snapshot, period_from, period_to,
                     uses_holdout bool, metrics_json, n_trials_family, notes)          -- G-12
research.holdout_access (experiment_id, accessed_at, by)                               -- ogni accesso all'hold-out è registrato

ledger.event        (seq bigserial, event_id uuid, occurred_at, recorded_at, account, kind, payload jsonb, prev_hash, hash)
ops.heartbeat       (component, at, status, detail)
ops.notification    (id, channel, sent_at, proposal_id, payload, delivered)
```
`ledger.event` è **a catena di hash** (`hash = sha256(prev_hash ‖ payload)`): una manomissione si rileva subito. Il DB ha un trigger che vieta UPDATE e DELETE.

## Eventi del ledger
| Evento | Payload principale |
|---|---|
| `Deposit` / `Withdrawal` | importo, data valuta |
| `ProposalCreated` | proposta completa (vedi [3.5](05-esecuzione-hybrid.md)) |
| `ProposalRejected` | violazioni dei guardrails (codici G-xx) |
| `ProposalNotified` / `Expired` / `Skipped` / `Superseded` | motivo |
| `OrderSubmitted` | broker, id ordine (live/paper) |
| `Fill` | strumento, quantità, prezzo, commissione, spread stimato, sede di esecuzione |
| `Dividend` / `WithholdingTax` | lordo, ritenuta estera, netto |
| `TaxWithheld` | trattenuta del broker (amministrato), da confrontare con il nostro calcolo |
| `StampDuty` | bollo addebitato |
| `RiskStateChanged` | da/a, equity, drawdown (eventi `money-core::risk`) |
| `ConfigChanged` | hash della nuova config, commit git |
| `Reconciliation` | differenze tra ledger ed estratto del broker |

## Proiezioni (viste materializzate, ricalcolabili)
- `positions` (quantità, costo medio ponderato), `cash`, `equity_daily`, `high_water_mark`.
- `tax_lots` e `zainetto` (vedi [3.4](04-costi-e-fisco.md)).
- `performance` (rendimenti netti giornalieri, benchmark).

## Retention e backup
- Dati raw: per sempre, compressi (Parquet su disco + Timescale compression).
- Backup notturno cifrato (`pg_dump` + `age`) verso un repo privato o un object storage gratuito. Il restore viene testato ogni mese da GitHub Actions.
