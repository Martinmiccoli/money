"""Connessione al DB, migrazioni e sincronizzazione dell'universo."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg

from .config import REPO_ROOT, Instrument

MIGRATIONS_DIR = REPO_ROOT / "infra" / "migrations"


def connect(url: str) -> psycopg.Connection:
    # autocommit: le transazioni sono esplicite (conn.transaction()).
    return psycopg.connect(url, autocommit=True)


def migrate(conn: psycopg.Connection, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Applica in ordine le migrazioni non ancora applicate. Ognuna in una transazione."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS public.schema_migrations ("
        " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    applied = {r[0] for r in conn.execute("SELECT version FROM public.schema_migrations")}
    done: list[str] = []
    for f in sorted(migrations_dir.glob("*.sql")):
        if f.stem in applied:
            continue
        with conn.transaction():
            conn.execute(f.read_text())
            conn.execute("INSERT INTO public.schema_migrations (version) VALUES (%s)", (f.stem,))
        done.append(f.stem)
    return done


def sync_universe(conn: psycopg.Connection, instruments: list[Instrument]) -> int:
    with conn.transaction():
        for i in instruments:
            conn.execute(
                """INSERT INTO ref.instrument
                       (instrument_id, name, asset_class, isin, currency, tax_category, sleeves, notes, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s, now())
                   ON CONFLICT (instrument_id) DO UPDATE SET
                       name=EXCLUDED.name, asset_class=EXCLUDED.asset_class, isin=EXCLUDED.isin,
                       currency=EXCLUDED.currency, tax_category=EXCLUDED.tax_category,
                       sleeves=EXCLUDED.sleeves, notes=EXCLUDED.notes, updated_at=now()""",
                (i.id, i.name, i.asset_class, i.isin, i.currency, i.tax_category, list(i.sleeves), i.notes),
            )
            conn.execute(
                """INSERT INTO ref.instrument_map (instrument_id, source, source_symbol, is_proxy, quote_currency)
                   VALUES (%s,%s,%s,true,%s)
                   ON CONFLICT (instrument_id, source) DO UPDATE SET
                       source_symbol=EXCLUDED.source_symbol, quote_currency=EXCLUDED.quote_currency""",
                (i.id, i.proxy.source, i.proxy.symbol, i.proxy.quote_currency),
            )
    return len(instruments)


@contextmanager
def ingest_run(conn: psycopg.Connection, job: str) -> Iterator[dict]:
    """Registra l'esecuzione di un job in ops.ingest_run (alimenta G-10 e il watchdog)."""
    run_id = conn.execute("INSERT INTO ops.ingest_run (job) VALUES (%s) RETURNING run_id", (job,)).fetchone()[0]
    state = {"rows": 0, "status": "ok", "detail": None}
    try:
        yield state
    except Exception as e:
        state["status"], state["detail"] = "failed", f"{type(e).__name__}: {e}"[:2000]
        raise
    finally:
        conn.execute(
            "UPDATE ops.ingest_run SET finished_at=now(), status=%s, rows_written=%s, detail=%s WHERE run_id=%s",
            (state["status"], state["rows"], state["detail"], run_id),
        )
        conn.execute(
            "INSERT INTO ops.heartbeat (component, status, detail) VALUES (%s,%s,%s)",
            (f"ingest:{job}", state["status"], state["detail"]),
        )
