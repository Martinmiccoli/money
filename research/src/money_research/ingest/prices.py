"""Ingest dei prezzi giornalieri dei proxy (Alpaca) nel DB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import psycopg

from ..config import Instrument
from .alpaca import AlpacaData, Bar

DEFAULT_START = date(2016, 1, 1)  # inizio dello storico Alpaca Basic
OVERLAP_DAYS = 7  # si riscarica qualche giorno per correzioni e rettifiche


@dataclass(frozen=True)
class Row:
    instrument_id: str
    bar: Bar
    adj_close: float | None
    currency: str


def merge_adjusted(raw: list[Bar], adjusted: list[Bar]) -> list[tuple[Bar, float | None]]:
    """Abbina a ogni barra non rettificata la chiusura rettificata (split + dividendi) dello stesso giorno."""
    adj = {b.date: b.close for b in adjusted}
    return [(b, adj.get(b.date)) for b in raw]


def last_dates(conn: psycopg.Connection) -> dict[str, date]:
    rows = conn.execute("SELECT instrument_id, max(date) FROM market.bar_1d GROUP BY instrument_id").fetchall()
    return {r[0]: r[1] for r in rows}


def incremental_start(instruments: list[Instrument], last: dict[str, date]) -> date:
    starts = [last[i.id] - timedelta(days=OVERLAP_DAYS) if i.id in last else DEFAULT_START for i in instruments]
    return min(starts) if starts else DEFAULT_START


def fetch(client: AlpacaData, instruments: list[Instrument], start: date, end: date | None) -> list[Row]:
    rows: list[Row] = []
    stocks = [i for i in instruments if i.proxy.source == "alpaca_stock"]
    cryptos = [i for i in instruments if i.proxy.source == "alpaca_crypto"]
    if stocks:
        syms = [i.proxy.symbol for i in stocks]
        raw = client.stock_bars(syms, start, end, adjustment="raw")
        adj = client.stock_bars(syms, start, end, adjustment="all")
        for i in stocks:
            for bar, a in merge_adjusted(raw.get(i.proxy.symbol, []), adj.get(i.proxy.symbol, [])):
                rows.append(Row(i.id, bar, a, i.proxy.quote_currency))
    if cryptos:
        bars = client.crypto_bars([i.proxy.symbol for i in cryptos], start, end)
        for i in cryptos:
            for bar in bars.get(i.proxy.symbol, []):
                rows.append(Row(i.id, bar, bar.close, i.proxy.quote_currency))
    return rows


def store(conn: psycopg.Connection, rows: list[Row]) -> int:
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO market.bar_1d
                   (instrument_id, date, source, currency, open, high, low, close, adj_close, volume, available_at)
               VALUES (%s,%s,'alpaca',%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (instrument_id, date, source) DO UPDATE SET
                   open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
                   adj_close=EXCLUDED.adj_close, volume=EXCLUDED.volume, ingested_at=now()""",
            [
                (
                    r.instrument_id,
                    r.bar.date,
                    r.currency,
                    r.bar.open,
                    r.bar.high,
                    r.bar.low,
                    r.bar.close,
                    r.adj_close,
                    r.bar.volume,
                    r.bar.available_at,
                )
                for r in rows
            ],
        )
    return len(rows)
