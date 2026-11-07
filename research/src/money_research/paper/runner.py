"""Paper trading lato Python: conti, feed dei prezzi, decisioni delle strategie (M6).

Il flusso di un giorno (vedi `run_day`):
1. ingest dei dati (prezzi, cambi, tassi)
2. feed dei prezzi EUR del paper (append-only)
3. `money-engine settle`: esegue gli ordini del giorno prima, interessi, bollo, versamenti
4. `decide`: le strategie (stesso codice del backtest) producono le intenzioni d'ordine
5. `money-engine execute`: guardrails (money-core), SimBroker, Alpaca ombra, valutazione, rischio

Le decisioni restano in Python, ma **i guardrails e l'esecuzione sono nel motore Rust**:
le strategie possono solo proporre, mai eseguire.
"""

from __future__ import annotations

import json
import pickle
import tomllib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import money_py as mc
import psycopg

from ..backtest.data import MarketData, load_market_data
from ..backtest.run import S3_CAPS, S3_UNIVERSE, _sectors, load_validation
from ..backtest.simulator import Context
from ..backtest.strategies import Combined, SavingsPlan, SectorRotation, TargetWeightStrategy, TrendFollowing
from ..config import REPO_ROOT

ROME = ZoneInfo("Europe/Rome")
PAPER_PATH = REPO_ROOT / "config" / "paper.toml"


@dataclass(frozen=True)
class Account:
    id: str
    strategy: str
    initial_deposit_eur: Decimal
    monthly_deposit_eur: Decimal
    notes: str = ""


def load_accounts(path: Path = PAPER_PATH) -> list[Account]:
    raw = tomllib.loads(path.read_text())
    out = []
    for a in raw.get("account", []):
        if a["strategy"] not in STRATEGIES:
            raise ValueError(f"strategia sconosciuta per {a['id']}: {a['strategy']}")
        out.append(
            Account(
                a["id"],
                a["strategy"],
                Decimal(str(a["initial_deposit_eur"])),
                Decimal(str(a.get("monthly_deposit_eur", 0))),
                a.get("notes", ""),
            )
        )
    return out


# ───────────────────────── strategie per nome (stesso codice del backtest) ─────────────────────────


def _s3(rebalance="monthly", vol_scaling=True) -> TrendFollowing:
    return TrendFollowing(
        name=f"S3 {rebalance}{' vol' if vol_scaling else ''}",
        rebalance=rebalance,
        universe=S3_UNIVERSE,
        vol_scaling=vol_scaling,
        caps=S3_CAPS,
    )


def _s4() -> SectorRotation:
    return SectorRotation(name="S4 top3 isteresi", sectors=_sectors(), top_k=3, hysteresis=True)


def _savings_plan():
    val = load_validation()
    return SavingsPlan(val["benchmark_instrument"], val["benchmark"]["expected_edge_pct"])


STRATEGIES = {
    "savings_plan": _savings_plan,
    "s3_monthly_equal": lambda: _s3("monthly", False),
    "s3_monthly_vol": lambda: _s3("monthly", True),
    "s4_top3": _s4,
    "s3s4_s8": lambda: Combined(name="S3+S4+S8", trend=_s3(), rotation=_s4(), use_regime=True),
}


def sync_accounts(conn: psycopg.Connection, accounts: list[Account], today: date) -> int:
    """Crea i conti nuovi. Quelli esistenti non cambiano data di partenza né capitale (G-12)."""
    n = 0
    for a in accounts:
        cur = conn.execute(
            """INSERT INTO paper.account
                   (account, strategy, initial_deposit_eur, monthly_deposit_eur, started_on, notes)
               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (account) DO NOTHING""",
            (a.id, a.strategy, a.initial_deposit_eur, a.monthly_deposit_eur, today, a.notes),
        )
        n += cur.rowcount
    return n


def all_instruments(accounts: list[Account]) -> list[str]:
    ids: set[str] = set()
    for a in accounts:
        ids |= set(STRATEGIES[a.strategy]().instruments)
    return sorted(ids)


# ───────────────────────── stato delle strategie ─────────────────────────


def warm_up(strategy, md: MarketData, until: datetime) -> None:
    """Scalda la stima dell'edge sulla storia: solo `targets()` a ogni inizio periodo, senza
    simulare profitti e perdite (nessuna metrica sull'hold-out). Poi il primo giorno ribilancia."""
    if not isinstance(strategy, TargetWeightStrategy):
        return
    val = load_validation()
    start = date(val["research_start"].year + 1, 1, 1)
    seen = None
    for d in md.calendar:
        if d < start or d >= until.date():
            continue
        period = strategy._period_of(d)
        if period == seen:
            continue
        seen = period
        ts = datetime.combine(d, val["decision_time"], tzinfo=ROME)
        strategy.targets(Context(d, md.view(ts), 0.0, {}, 0.0, "Active"))
    strategy._period = None  # il primo giorno di paper ribilancia subito


def load_strategy(conn: psycopg.Connection, account: Account, md: MarketData, now: datetime):
    row = conn.execute("SELECT state FROM paper.strategy_state WHERE account=%s", (account.id,)).fetchone()
    if row:
        return pickle.loads(row[0])
    s = STRATEGIES[account.strategy]()
    warm_up(s, md, now)
    return s


def save_strategy(conn: psycopg.Connection, account: Account, strategy) -> None:
    conn.execute(
        """INSERT INTO paper.strategy_state (account, state) VALUES (%s,%s)
           ON CONFLICT (account) DO UPDATE SET state=EXCLUDED.state, saved_at=now()""",
        (account.id, pickle.dumps(strategy)),
    )


# ───────────────────────── decisione ─────────────────────────


def _ledger(conn: psycopg.Connection, account: str) -> mc.Ledger:
    rows = conn.execute("SELECT record FROM ledger.event WHERE account=%s ORDER BY seq", (account,)).fetchall()
    return mc.Ledger.from_records(account, json.dumps([r[0] for r in rows]))


def decide(conn: psycopg.Connection, accounts: list[Account], now: datetime) -> dict[str, str]:
    """Scrive le intenzioni d'ordine di oggi in paper.intent. Idempotente: una volta al giorno."""
    if now.tzinfo is None:
        raise ValueError("now deve avere il fuso orario")
    val = load_validation()
    md = load_market_data(conn, all_instruments(accounts), val["proxy_drag_bps_per_year"], set(val["fx_hedged"]))
    today = now.astimezone(ROME).date()
    out = {}
    for a in accounts:
        if conn.execute(
            "SELECT 1 FROM paper.intent WHERE account=%s AND (decided_at AT TIME ZONE 'Europe/Rome')::date=%s",
            (a.id, today),
        ).fetchone():
            out[a.id] = "già deciso oggi"
            continue
        if conn.execute("SELECT 1 FROM paper.order WHERE account=%s AND status='pending'", (a.id,)).fetchone():
            out[a.id] = "ordini in attesa di esecuzione: decisione rimandata"
            continue
        led = _ledger(conn, a.id)
        if len(led) == 0:
            out[a.id] = "conto senza versamento iniziale: esegui prima money-engine settle"
            continue
        pf = json.loads(led.portfolio_json())
        holdings = {k: Decimal(v["qty"]) for k, v in pf["holdings"].items()}
        view = md.view(now)
        cash = float(pf["cash_eur"])
        equity = cash + sum(float(q) * (view.last_close(k) or 0.0) for k, q in holdings.items())
        state = conn.execute(
            "SELECT risk_state FROM paper.equity_daily WHERE account=%s ORDER BY date DESC LIMIT 1", (a.id,)
        ).fetchone()
        strategy = load_strategy(conn, a, md, now)
        intents = strategy.decide(Context(today, view, cash, holdings, equity, state[0] if state else "Active"))
        with conn.transaction():
            for it in intents:
                conn.execute(
                    """INSERT INTO paper.intent (account, decided_at, instrument_id, side, notional_eur, qty,
                                                 order_kind, expected_edge_pct, reason)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        a.id,
                        now,
                        it.instrument,
                        it.side,
                        None if it.notional_eur is None else Decimal(str(round(it.notional_eur, 2))),
                        it.qty,
                        it.kind,
                        None if it.expected_edge_pct is None else Decimal(str(round(it.expected_edge_pct, 4))),
                        it.reason,
                    ),
                )
            save_strategy(conn, a, strategy)
        out[a.id] = f"{len(intents)} intenzioni" if intents else "nessun ordine"
    return out


def next_weekday(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


# ───────────────────────── orchestrazione della giornata ─────────────────────────

ENGINE_DIR = REPO_ROOT / "engine"
ENGINE_BIN = ENGINE_DIR / "target" / "release" / "money-engine"


def engine(cmd: str, now: datetime | None = None) -> str:
    """Esegue `money-engine <cmd>` (lo compila se manca)."""
    import os
    import shutil
    import subprocess

    if not ENGINE_BIN.exists():
        cargo = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")
        subprocess.run([cargo, "build", "--release", "-p", "money-engine"], cwd=ENGINE_DIR, check=True)
    args = [str(ENGINE_BIN), cmd]
    if now is not None:
        args += ["--now", now.astimezone(ZoneInfo("UTC")).isoformat()]
    r = subprocess.run(
        args, cwd=REPO_ROOT, capture_output=True, text=True, env={**os.environ, "MONEY_REPO": str(REPO_ROOT)}
    )
    if r.returncode != 0:
        raise RuntimeError(f"money-engine {cmd} fallito:\n{r.stderr.strip()}")
    return r.stdout.strip()


def status_rows(conn: psycopg.Connection) -> list[dict]:
    """Riepilogo del Gate 1 per conto: valore, rendimento, ordini, rifiuti, rischio."""
    out = []
    for acct, strategy, started, deposit in conn.execute(
        "SELECT account, strategy, started_on, initial_deposit_eur FROM paper.account ORDER BY account"
    ).fetchall():
        eq = conn.execute(
            """SELECT date, nav_eur, net_deposits_eur, risk_state FROM paper.equity_daily
               WHERE account=%s ORDER BY date""",
            (acct,),
        ).fetchall()
        kinds = dict(
            conn.execute("SELECT kind, count(*) FROM ledger.event WHERE account=%s GROUP BY kind", (acct,)).fetchall()
        )
        codes = conn.execute(
            """SELECT c, count(*) FROM ledger.event, jsonb_array_elements_text(record->'event'->'codes') c
               WHERE account=%s AND kind='OrderRejected' GROUP BY c ORDER BY 2 DESC""",
            (acct,),
        ).fetchall()
        navs = [float(r[1]) for r in eq]
        peak, mdd = 0.0, 0.0
        for v in navs:
            peak = max(peak, v)
            mdd = min(mdd, v / peak - 1) if peak > 0 else mdd
        out.append(
            {
                "conto": acct,
                "strategia": strategy,
                "dal": started,
                "giorni": len(eq),
                "valore": navs[-1] if navs else None,
                "versato": float(eq[-1][2]) if eq else float(deposit),
                "rendimento": (navs[-1] / float(eq[-1][2]) - 1) if eq and float(eq[-1][2]) > 0 else None,
                "max_dd": mdd,
                "eseguiti": kinds.get("Fill", 0),
                "rifiutati": ", ".join(f"{c}×{n}" for c, n in codes) or "—",
                "rischio": eq[-1][3] if eq else "—",
            }
        )
    return out
