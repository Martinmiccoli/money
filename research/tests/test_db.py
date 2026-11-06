"""Test di integrazione sul DB reale: saltati se DATABASE_URL non è raggiungibile."""

import os
from datetime import date

import psycopg
import pytest

from money_research import db
from money_research.config import load_universe
from money_research.ingest import ecb

URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.fixture
def conn():
    if not URL:
        pytest.skip("TEST_DATABASE_URL non impostato")
    try:
        c = db.connect(URL)
    except psycopg.OperationalError:
        pytest.skip("database non raggiungibile")
    yield c
    c.close()


@pytest.mark.db
def test_migrate_is_idempotent_and_upserts(conn):
    db.migrate(conn)
    assert db.migrate(conn) == []
    db.sync_universe(conn, load_universe())
    r = [ecb.FxRate("EURTEST", date(2026, 1, 2), 1.1)]
    ecb.store(conn, r)
    ecb.store(conn, [ecb.FxRate("EURTEST", date(2026, 1, 2), 1.2)])
    assert conn.execute("SELECT rate FROM market.fx_1d WHERE pair='EURTEST'").fetchone()[0] == 1.2
    conn.execute("DELETE FROM market.fx_1d WHERE pair='EURTEST'")


@pytest.mark.db
def test_bar_constraints(conn):
    db.migrate(conn)
    db.sync_universe(conn, load_universe())
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO market.bar_1d (instrument_id,date,source,currency,open,high,low,close,available_at) "
            "VALUES ('us_equity','1990-01-01','test','USD',1,1,2,1,now())"
        )
