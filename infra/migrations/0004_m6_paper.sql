-- M6: paper trading (docs/03-system-design/05-esecuzione-hybrid.md, Gate 1).
-- Flusso giornaliero: ingest → feed prezzi → engine settle → decide (Python) → engine execute.
CREATE SCHEMA IF NOT EXISTS paper;

-- Conti paper (da config/paper.toml).
CREATE TABLE paper.account (
    account             text PRIMARY KEY,
    strategy            text NOT NULL,
    initial_deposit_eur numeric NOT NULL CHECK (initial_deposit_eur > 0),
    monthly_deposit_eur numeric NOT NULL DEFAULT 0 CHECK (monthly_deposit_eur >= 0),
    started_on          date NOT NULL,
    active              boolean NOT NULL DEFAULT true,
    notes               text
);

-- Prezzo "UCITS sintetico" in EUR, costruito giorno per giorno dal proxy e MAI riscritto.
-- Le serie rettificate dei proxy cambiano retroattivamente a ogni dividendo: qui si salva solo il
-- rendimento del giorno, così le valutazioni del ledger restano coerenti nel tempo.
CREATE TABLE paper.price_eur (
    instrument_id   text NOT NULL REFERENCES ref.instrument,
    date            date NOT NULL,
    open_eur        numeric NOT NULL CHECK (open_eur > 0),
    close_eur       numeric NOT NULL CHECK (close_eur > 0),
    available_at    timestamptz NOT NULL,       -- G-11: dalla disponibilità della barra del proxy
    computed_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_id, date)
);

-- Intenzioni d'ordine prodotte dalle strategie (Python), da controllare ed eseguire (Rust).
CREATE TABLE paper.intent (
    intent_id       bigserial PRIMARY KEY,
    account         text NOT NULL REFERENCES paper.account,
    decided_at      timestamptz NOT NULL,
    instrument_id   text NOT NULL,
    side            text NOT NULL CHECK (side IN ('buy','sell')),
    notional_eur    numeric,                    -- acquisti: contanti da impiegare
    qty             numeric,                    -- vendite: quantità
    order_kind      text NOT NULL DEFAULT 'regular' CHECK (order_kind IN ('regular','savings_plan')),
    expected_edge_pct numeric,
    reason          text NOT NULL DEFAULT '',
    status          text NOT NULL DEFAULT 'new' CHECK (status IN ('new','rejected','submitted')),
    processed_at    timestamptz,
    CHECK ((side = 'buy' AND notional_eur > 0) OR (side = 'sell' AND (qty > 0 OR notional_eur > 0)))
);
CREATE INDEX ON paper.intent (account, status);

-- Ordini accettati dai guardrails, in attesa del prezzo di esecuzione (SimBroker).
CREATE TABLE paper.order (
    order_id        text PRIMARY KEY,
    account         text NOT NULL REFERENCES paper.account,
    intent_id       bigint REFERENCES paper.intent,
    instrument_id   text NOT NULL,
    side            text NOT NULL,
    notional_eur    numeric,
    qty             numeric,
    order_kind      text NOT NULL,
    exec_date       date NOT NULL,              -- giorno di borsa in cui si esegue all'apertura
    status          text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','filled','expired')),
    created_at      timestamptz NOT NULL DEFAULT now(),
    settled_at      timestamptz,
    fill            jsonb
);
CREATE INDEX ON paper.order (account, status);

-- Copia "ombra" degli ordini su Alpaca Paper: solo per confrontare il fill simulato con uno reale.
CREATE TABLE paper.alpaca_shadow (
    order_id        text PRIMARY KEY REFERENCES paper.order,
    alpaca_order_id text,
    symbol          text NOT NULL,
    side            text NOT NULL,
    notional_usd    numeric,
    qty             numeric,
    status          text NOT NULL,
    submitted_at    timestamptz NOT NULL DEFAULT now(),
    filled_at       timestamptz,
    filled_avg_price_usd numeric,
    detail          text
);

-- Valore del conto a fine giornata e stato del rischio (base del report del Gate 1).
CREATE TABLE paper.equity_daily (
    account         text NOT NULL REFERENCES paper.account,
    date            date NOT NULL,
    nav_eur         numeric NOT NULL,
    cash_eur        numeric NOT NULL,
    invested_eur    numeric NOT NULL,
    net_deposits_eur numeric NOT NULL,
    high_water_mark_eur double precision NOT NULL,
    risk_state      text NOT NULL,
    computed_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (account, date)
);

-- Stato interno delle strategie (es. stima dell'edge), salvato tra un giorno e l'altro.
CREATE TABLE paper.strategy_state (
    account         text PRIMARY KEY REFERENCES paper.account,
    saved_at        timestamptz NOT NULL DEFAULT now(),
    state           bytea NOT NULL
);

CREATE FUNCTION paper.forbid_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% è append-only: % vietato', TG_TABLE_NAME, TG_OP;
END $$;
CREATE TRIGGER price_append_only BEFORE UPDATE OR DELETE ON paper.price_eur
    FOR EACH ROW EXECUTE FUNCTION paper.forbid_change();
