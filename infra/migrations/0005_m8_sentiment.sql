-- M8: serie giornaliere di sentiment e attenzione (S6). Ogni valore ha il suo available_at (G-11).
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE raw.daily_series (
    source          text        NOT NULL,       -- 'wikipedia' | 'gdelt' | 'alternative_me'
    series_id       text        NOT NULL,       -- es. 'Bitcoin', 'crash_narrative', 'fear_greed'
    date            date        NOT NULL,
    value           double precision NOT NULL,
    available_at    timestamptz NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source, series_id, date)
);
