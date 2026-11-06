-- M3: tassi privi di rischio, registro degli esperimenti (G-12) e accessi all'hold-out.
-- Vedi docs/03-system-design/06-backtest-e-metriche.md.

-- Tassi giornalieri (BCE): €STR e EONIA, in % annua.
CREATE TABLE market.rate_1d (
    series          text        NOT NULL,       -- 'ESTR' | 'EONIA'
    date            date        NOT NULL,
    rate_pct        double precision NOT NULL,
    source          text        NOT NULL,
    available_at    timestamptz NOT NULL,       -- G-11
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (series, date, source)
);

CREATE SCHEMA IF NOT EXISTS research;

-- G-12: ogni esecuzione del simulatore viene registrata, anche quelle andate male.
CREATE TABLE research.experiment (
    experiment_id   bigserial   PRIMARY KEY,
    created_at      timestamptz NOT NULL DEFAULT now(),
    family          text        NOT NULL,       -- famiglia di tentativi (per il Deflated Sharpe)
    strategy        text        NOT NULL,
    code_version    text        NOT NULL,       -- commit git (+ "-dirty" se ci sono modifiche)
    config_json     jsonb       NOT NULL,
    data_snapshot   text        NOT NULL,       -- hash dei dati usati
    period_from     date        NOT NULL,
    period_to       date        NOT NULL,
    uses_holdout    boolean     NOT NULL,
    metrics_json    jsonb       NOT NULL,
    n_trials_family integer     NOT NULL,       -- tentativi della famiglia, questo incluso
    report_path     text,
    notes           text
);
CREATE INDEX ON research.experiment (family, created_at);

-- Ogni accesso all'hold-out resta tracciato. Dal secondo accesso la famiglia è "contaminata".
CREATE TABLE research.holdout_access (
    id              bigserial   PRIMARY KEY,
    family          text        NOT NULL,
    accessed_at     timestamptz NOT NULL DEFAULT now(),
    by              text        NOT NULL,
    purpose         text        NOT NULL
);
CREATE INDEX ON research.holdout_access (family);

-- Il registro non si riscrive: niente UPDATE né DELETE (un tentativo andato male conta lo stesso).
CREATE FUNCTION research.forbid_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% è append-only: % vietato (G-12)', TG_TABLE_NAME, TG_OP;
END $$;

CREATE TRIGGER experiment_append_only BEFORE UPDATE OR DELETE ON research.experiment
    FOR EACH ROW EXECUTE FUNCTION research.forbid_change();
CREATE TRIGGER holdout_append_only BEFORE UPDATE OR DELETE ON research.holdout_access
    FOR EACH ROW EXECUTE FUNCTION research.forbid_change();
