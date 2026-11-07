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


@pytest.mark.db
def test_registro_esperimenti_append_only(conn):
    from money_research.backtest import registry

    db.migrate(conn)
    # Tutto in una transazione annullata: il registro vero non si sporca (non si può più pulire).
    with conn.transaction(force_rollback=True):
        args = dict(
            family="test-famiglia",
            strategy="s",
            config={"x": float("nan")},
            data_snapshot="abc",
            period=(date(2020, 1, 1), date(2020, 12, 31)),
            uses_holdout=False,
            metrics={"sharpe_daily": 0.05},
        )
        _, n1 = registry.record(conn, **args)
        _, n2 = registry.record(conn, **{**args, "metrics": {"sharpe_daily": 0.07}})
        assert (n1, n2) == (1, 2)
        stats = registry.family_stats(conn, "test-famiglia")
        assert stats.n_trials == 2 and stats.var_sharpe_daily == pytest.approx(0.0002)
        assert registry.register_holdout_access(conn, "test-famiglia", "test", "prova") == 1
        assert registry.register_holdout_access(conn, "test-famiglia", "test", "prova") == 2
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"), conn.transaction():
            conn.execute("DELETE FROM research.experiment WHERE family='test-famiglia'")


@pytest.mark.db
def test_feed_paper_rendimenti_concatenati_e_append_only(conn):
    """Il feed salva solo il rendimento del giorno: un dividendo che riscrive lo storico rettificato
    non cambia i prezzi già salvati. Tutto in una transazione annullata."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from money_research.paper.feed import update_feed

    db.migrate(conn)
    ny = ZoneInfo("America/New_York")
    with conn.transaction(force_rollback=True):
        conn.execute(
            "INSERT INTO ref.instrument (instrument_id, name, asset_class, currency, tax_category)"
            " VALUES ('test_etf','t','etf_ucits','EUR','RC')"
        )

        def bar(d, close, adj):
            conn.execute(
                """INSERT INTO market.bar_1d (instrument_id, date, source, currency, open, high, low, close,
                                              adj_close, volume, available_at)
                   VALUES ('test_etf',%s,'test','EUR',%s,%s,%s,%s,%s,0,%s)""",
                (d, close, close, close, close, adj, datetime(d.year, d.month, d.day, 17, tzinfo=ny)),
            )

        bar(date(2026, 1, 5), 100, 100)
        bar(date(2026, 1, 6), 110, 110)
        n = update_feed(conn, ["test_etf"], date(2026, 1, 5), {"test_etf": 0}, set())
        assert n == 2
        # Dividendo: lo storico rettificato viene riscritto (−2%), poi arriva il 7/1.
        conn.execute("UPDATE market.bar_1d SET adj_close = adj_close * 0.98 WHERE instrument_id='test_etf'")
        bar(date(2026, 1, 7), 99, 99 * 1.0)  # chiusura 99 dopo uno stacco di 2,2 (adj = 99)
        update_feed(conn, ["test_etf"], date(2026, 1, 5), {"test_etf": 0}, set())
        rows = conn.execute(
            "SELECT date, close_eur FROM paper.price_eur WHERE instrument_id='test_etf' ORDER BY date"
        ).fetchall()
        closes = [float(r[1]) for r in rows]
        assert closes[:2] == [100.0, 110.0]  # i prezzi già salvati non cambiano
        # rendimento del 7/1 = 99 / (110 × 0,98) − 1, applicato al prezzo salvato del 6/1
        assert closes[2] == pytest.approx(110 * 99 / (110 * 0.98), rel=1e-6)
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"), conn.transaction():
            conn.execute("UPDATE paper.price_eur SET close_eur = 1 WHERE instrument_id='test_etf'")
