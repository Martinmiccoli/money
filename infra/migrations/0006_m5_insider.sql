-- M5: acquisti e vendite degli insider (Form 4) e prezzi delle singole azioni (S1).
CREATE TABLE raw.form4 (
    accession_no    text        NOT NULL,
    trans_sk        bigint      NOT NULL,       -- chiave della transazione nel dataset SEC
    issuer_cik      text        NOT NULL,
    symbol          text,                       -- simbolo dichiarato nel filing (può essere vecchio)
    owner_cik       text        NOT NULL,
    owner_name      text,
    relationship    text,                       -- Director, Officer, TenPercentOwner, Other (anche combinati)
    officer_title   text,
    trans_code      text        NOT NULL,       -- P = acquisto sul mercato, S = vendita
    trans_date      date,
    shares          double precision,
    price           double precision,
    shares_after    double precision,
    is_10b5_1       boolean     NOT NULL DEFAULT false,
    filing_date     date        NOT NULL,
    available_at    timestamptz NOT NULL,       -- G-11: fine della giornata di deposito (22:00 New York)
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (accession_no, trans_sk)
);
CREATE INDEX ON raw.form4 (filing_date, trans_code);
CREATE INDEX ON raw.form4 (owner_cik, trans_date);
CREATE INDEX ON raw.form4 (symbol);

-- Barre giornaliere delle singole azioni USA (Alpaca), solo per gli emittenti con segnali S1.
CREATE TABLE market.stock_bar_1d (
    symbol          text        NOT NULL,
    date            date        NOT NULL,
    open            double precision NOT NULL,
    high            double precision NOT NULL,
    low             double precision NOT NULL,
    close           double precision NOT NULL,
    adj_close       double precision,
    volume          double precision,
    available_at    timestamptz NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, date)
);
SELECT create_hypertable('market.stock_bar_1d', 'date', chunk_time_interval => interval '1 year');
