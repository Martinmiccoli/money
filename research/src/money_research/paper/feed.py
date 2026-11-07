"""Feed dei prezzi del paper trading: prezzo "UCITS sintetico" in EUR, append-only.

Le serie rettificate dei proxy (Alpaca, adjustment=all) cambiano retroattivamente a ogni dividendo.
Il ledger però registra fill a prezzi fissi: per valutarlo in modo coerente serve una serie che non
cambi mai. Qui si salva, giorno per giorno, solo il **rendimento** del proxy (rettificato, quindi
"ad accumulo"), convertito in EUR e ridotto del drag annuo stimato — come nel backtest (data.py).

    close_eur(d) = close_eur(d-1) · adj(d)/adj(d-1) · fx(d-1)/fx(d) · drag
    open_eur(d)  = close_eur(d-1) · adj_open(d)/adj(d-1) · fx(d-1)/fx(d) · drag
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import psycopg

from ..backtest.data import load_market_data

Q = Decimal("0.00000001")


def _bars(conn: psycopg.Connection, instrument: str) -> pd.DataFrame:
    df = pd.DataFrame(
        conn.execute(
            """SELECT date, open, close, adj_close, currency, available_at FROM market.bar_1d
               WHERE instrument_id=%s ORDER BY date""",
            (instrument,),
        ).fetchall(),
        columns=["date", "open", "close", "adj_close", "currency", "available_at"],
    )
    df["adj"] = df["adj_close"].fillna(df["close"])
    df["adj_open"] = df["open"] * df["adj"] / df["close"]
    return df


def _fx(conn: psycopg.Connection) -> pd.Series:
    rows = conn.execute("SELECT date, rate FROM market.fx_1d WHERE pair='EURUSD' ORDER BY date").fetchall()
    return pd.Series([r[1] for r in rows], index=pd.to_datetime([r[0] for r in rows]))


def update_feed(
    conn: psycopg.Connection,
    instruments: list[str],
    anchor: date,
    drag_bps: dict[str, float],
    fx_hedged: set[str],
) -> int:
    """Aggiunge al feed i giorni nuovi. Il primo valore (all'àncora) è il prezzo del backtest."""
    fx = _fx(conn)
    added = 0
    for inst in instruments:
        last = conn.execute(
            "SELECT date, close_eur FROM paper.price_eur WHERE instrument_id=%s ORDER BY date DESC LIMIT 1",
            (inst,),
        ).fetchone()
        bars = _bars(conn, inst)
        if bars.empty:
            continue
        hedged = inst in fx_hedged
        bps = drag_bps.get(inst, drag_bps.get("default", 0.0))
        rows = []
        if last is None:
            md = load_market_data(conn, [inst], drag_bps, fx_hedged)
            s = md.series[inst]
            start_idx = int(pd.Index(pd.to_datetime(s.dates)).searchsorted(pd.Timestamp(anchor)))
            start_idx = min(start_idx, len(s.dates) - 1)
            d0 = pd.Timestamp(s.dates[start_idx]).date()
            b0 = bars[bars["date"] == d0].iloc[0]
            c0 = Decimal(str(s.close_eur[start_idx])).quantize(Q)
            o0 = Decimal(str(s.open_eur[start_idx])).quantize(Q)
            rows.append((inst, d0, o0, c0, b0["available_at"]))
            prev_date, prev_close = d0, c0
        else:
            prev_date, prev_close = last
        new = bars[bars["date"] > prev_date]
        prev = bars[bars["date"] == prev_date]
        if prev.empty:
            continue
        p_adj = float(prev["adj"].iloc[0])
        for _, b in new.iterrows():
            if hedged or b["currency"] == "EUR":
                fxf = 1.0
            else:
                f_prev = fx.asof(pd.Timestamp(prev_date))
                f_now = fx.asof(pd.Timestamp(b["date"]))
                if pd.isna(f_prev) or pd.isna(f_now):
                    break  # cambio non ancora disponibile: si riprova al prossimo giro
                fxf = float(f_prev) / float(f_now)
            drag = math.exp(-bps / 10_000 * (b["date"] - prev_date).days / 365.25)
            close = (prev_close * Decimal(str(float(b["adj"]) / p_adj * fxf * drag))).quantize(Q)
            open_ = (prev_close * Decimal(str(float(b["adj_open"]) / p_adj * fxf * drag))).quantize(Q)
            rows.append((inst, b["date"], open_, close, b["available_at"]))
            prev_date, prev_close, p_adj = b["date"], close, float(b["adj"])
        if rows:
            with conn.transaction(), conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO paper.price_eur (instrument_id, date, open_eur, close_eur, available_at)
                       VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    rows,
                )
            added += len(rows)
    return added


def default_anchor(started_on: date) -> date:
    """Il feed parte qualche giorno prima del primo conto, per avere una valutazione al giorno 1."""
    return started_on - timedelta(days=10)
