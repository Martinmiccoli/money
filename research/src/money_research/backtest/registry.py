"""Registro degli esperimenti (G-12) e accessi all'hold-out.

Ogni esecuzione del simulatore viene registrata, anche quelle andate male: il Deflated Sharpe
di una strategia si calcola sul numero **totale** di tentativi della sua famiglia.
"""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from datetime import date

import psycopg

from ..config import REPO_ROOT


def code_version() -> str:
    """Commit corrente, con "-dirty" se ci sono modifiche non committate."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@dataclass(frozen=True)
class FamilyStats:
    n_trials: int  # tentativi già registrati
    var_sharpe_daily: float  # varianza degli Sharpe giornalieri tra i tentativi


def family_stats(conn: psycopg.Connection, family: str) -> FamilyStats:
    rows = conn.execute(
        "SELECT (metrics_json->>'sharpe_daily')::float FROM research.experiment WHERE family=%s", (family,)
    ).fetchall()
    srs = [r[0] for r in rows if r[0] is not None and math.isfinite(r[0])]
    var = 0.0
    if len(srs) > 1:
        mean = sum(srs) / len(srs)
        var = sum((s - mean) ** 2 for s in srs) / (len(srs) - 1)
    return FamilyStats(len(rows), var)


def _clean(obj):
    """JSON senza NaN/inf (Postgres jsonb non li accetta)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_clean(v) for v in obj]
    return obj


def record(
    conn: psycopg.Connection,
    *,
    family: str,
    strategy: str,
    config: dict,
    data_snapshot: str,
    period: tuple[date, date],
    uses_holdout: bool,
    metrics: dict,
    report_path: str | None = None,
    notes: str | None = None,
) -> tuple[int, int]:
    """Registra un esperimento. Restituisce (id, tentativi della famiglia incluso questo)."""
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('experiment:' || %s))", (family,))
        n = conn.execute("SELECT count(*) FROM research.experiment WHERE family=%s", (family,)).fetchone()[0] + 1
        eid = conn.execute(
            """INSERT INTO research.experiment
                 (family, strategy, code_version, config_json, data_snapshot, period_from, period_to,
                  uses_holdout, metrics_json, n_trials_family, report_path, notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING experiment_id""",
            (
                family,
                strategy,
                code_version(),
                json.dumps(_clean(config), default=str),
                data_snapshot,
                period[0],
                period[1],
                uses_holdout,
                json.dumps(_clean(metrics), default=str),
                n,
                report_path,
                notes,
            ),
        ).fetchone()[0]
    return eid, n


def register_holdout_access(conn: psycopg.Connection, family: str, by: str, purpose: str) -> int:
    """Registra l'accesso all'hold-out. Restituisce il numero di accessi della famiglia (questo incluso).
    Dal secondo accesso l'hold-out della famiglia è contaminato e il report non può superare il Gate 0."""
    conn.execute("INSERT INTO research.holdout_access (family, by, purpose) VALUES (%s,%s,%s)", (family, by, purpose))
    return conn.execute("SELECT count(*) FROM research.holdout_access WHERE family=%s", (family,)).fetchone()[0]
