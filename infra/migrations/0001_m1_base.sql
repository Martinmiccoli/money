-- M1: anagrafica strumenti, prezzi giornalieri, cambi, operatività.
-- Vedi docs/03-system-design/03-dati-e-ledger.md
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS ops;

-- Strumenti. instrument_id è una chiave leggibile e stabile (es. 'world_equity').
CREATE TABLE ref.instrument (
    instrument_id   text PRIMARY KEY,
    name            text NOT NULL,
    asset_class     text NOT NULL CHECK (asset_class IN ('stock_us','etf_ucits','etf_us','crypto_etp','crypto_spot')),
    isin            text,                       -- strumento reale negoziato (UCITS / ETP); NULL se da verificare
    currency        text NOT NULL,
    tax_category    text CHECK (tax_category IN ('RD','RC','CRYPTO')),
    sleeves         text[] NOT NULL DEFAULT '{}',
    notes           text,
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Simbolo usato da ogni fonte per lo strumento (es. proxy USA su Alpaca).
CREATE TABLE ref.instrument_map (
    instrument_id   text NOT NULL REFERENCES ref.instrument ON DELETE CASCADE,
    source          text NOT NULL,              -- 'alpaca_stock' | 'alpaca_crypto' | ...
    source_symbol   text NOT NULL,
    is_proxy        boolean NOT NULL DEFAULT false,
    quote_currency  text NOT NULL,
    PRIMARY KEY (instrument_id, source)
);

-- Barre giornaliere. close = non rettificato; adj_close = rettificato split+dividendi (total return).
CREATE TABLE market.bar_1d (
    instrument_id   text NOT NULL REFERENCES ref.instrument,
    date            date NOT NULL,
    source          text NOT NULL,
    currency        text NOT NULL,
    open            double precision NOT NULL,
    high            double precision NOT NULL,
    low             double precision NOT NULL,
    close           double precision NOT NULL,
    adj_close       double precision,
    volume          double precision,
    available_at    timestamptz NOT NULL,       -- G-11: da quando il dato è utilizzabile
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_id, date, source),
    CHECK (high >= low AND open > 0 AND close > 0)
);
SELECT create_hypertable('market.bar_1d', 'date', chunk_time_interval => interval '1 year');

-- Cambi BCE. rate = unità di valuta quotata per 1 unità di base (EURUSD 1.08 = 1 EUR -> 1.08 USD).
CREATE TABLE market.fx_1d (
    pair            text NOT NULL,
    date            date NOT NULL,
    rate            double precision NOT NULL CHECK (rate > 0),
    source          text NOT NULL,
    available_at    timestamptz NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (pair, date, source)
);

-- Registro delle esecuzioni dei job di ingest (alimenta G-10 e il watchdog).
CREATE TABLE ops.ingest_run (
    run_id          bigserial PRIMARY KEY,
    job             text NOT NULL,
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    status          text NOT NULL DEFAULT 'running' CHECK (status IN ('running','ok','partial','failed')),
    rows_written    integer NOT NULL DEFAULT 0,
    detail          text
);

CREATE TABLE ops.heartbeat (
    component       text NOT NULL,
    at              timestamptz NOT NULL DEFAULT now(),
    status          text NOT NULL,
    detail          text
);
CREATE INDEX ON ops.heartbeat (component, at DESC);
