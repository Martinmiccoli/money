-- M2: ledger append-only a catena di hash (docs/03-system-design/03-dati-e-ledger.md, G-16).
-- Il record completo, così come lo serializza money-core, sta in `record` (jsonb): rileggendolo,
-- money-core ricalcola l'hash e verifica la catena. Le altre colonne servono solo alle query.
CREATE SCHEMA IF NOT EXISTS ledger;

CREATE TABLE ledger.event (
    account         text        NOT NULL,
    seq             bigint      NOT NULL CHECK (seq >= 1),
    event_id        text        NOT NULL UNIQUE,
    kind            text        NOT NULL,
    date            date        NOT NULL,
    occurred_at     timestamptz NOT NULL,
    record          jsonb       NOT NULL,
    prev_hash       char(64)    NOT NULL,
    hash            char(64)    NOT NULL UNIQUE,
    inserted_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (account, seq),
    CHECK (record->>'hash' = hash AND record->>'prev_hash' = prev_hash
           AND (record->>'seq')::bigint = seq AND record->>'account' = account)
);
CREATE INDEX ON ledger.event (account, kind, date);

-- Append-only: nessuna modifica né cancellazione, nemmeno per errore.
CREATE FUNCTION ledger.forbid_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'ledger.event è append-only: % vietato (G-16)', TG_OP;
END $$;

CREATE TRIGGER event_no_update_delete BEFORE UPDATE OR DELETE ON ledger.event
    FOR EACH ROW EXECUTE FUNCTION ledger.forbid_change();
CREATE TRIGGER event_no_truncate BEFORE TRUNCATE ON ledger.event
    FOR EACH STATEMENT EXECUTE FUNCTION ledger.forbid_change();

-- Seconda linea di difesa: ogni nuovo record deve agganciarsi all'ultimo del suo conto.
-- (La verifica crittografica completa la fa money-core.)
CREATE FUNCTION ledger.check_link() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    last_seq  bigint;
    last_hash char(64);
BEGIN
    -- Serializza gli append concorrenti sullo stesso conto.
    PERFORM pg_advisory_xact_lock(hashtext('ledger:' || NEW.account));
    SELECT seq, hash INTO last_seq, last_hash
      FROM ledger.event WHERE account = NEW.account ORDER BY seq DESC LIMIT 1;
    IF last_seq IS NULL THEN
        IF NEW.seq <> 1 OR NEW.prev_hash <> repeat('0', 64) THEN
            RAISE EXCEPTION 'primo evento del conto %: seq deve essere 1 e prev_hash il genesis', NEW.account;
        END IF;
    ELSIF NEW.seq <> last_seq + 1 OR NEW.prev_hash <> last_hash THEN
        RAISE EXCEPTION 'catena rotta sul conto %: atteso seq % con prev_hash %', NEW.account, last_seq + 1, last_hash;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER event_check_link BEFORE INSERT ON ledger.event
    FOR EACH ROW EXECUTE FUNCTION ledger.check_link();
