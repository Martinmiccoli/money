"""Serie di sentiment e attenzione (S6) e storico crypto lungo (laboratorio crypto). Tutto gratuito.

| Fonte | Serie | Disponibile (G-11, prudente) |
|---|---|---|
| Wikimedia pageviews | visite giornaliere di una voce (es. "Bitcoin") | giorno d+1 alle 06:00 UTC |
| GDELT DOC 2.0 (timelinevol) | % di articoli mondiali che citano un tema | giorno d+1 alle 01:00 UTC |
| alternative.me | Crypto Fear & Greed Index (0-100) | giorno d alle 01:00 UTC |
| Binance (dati pubblici) | barre giornaliere BTCUSDT dal 2017 | giorno d+1 alle 00:10 UTC |
"""

from __future__ import annotations

import logging
import os
import time as _time
from datetime import UTC, date, datetime, time, timedelta

import httpx
import psycopg

log = logging.getLogger(__name__)
UA = {"User-Agent": "money-research/0.1 (personal research project)"}


def wikimedia_headers() -> dict[str, str] | None:
    """La policy di Wikimedia (https://w.wiki/4wJS) chiede un contatto nello User-Agent.
    Si imposta in .env (WIKIMEDIA_CONTACT = email o URL); senza, Wikipedia viene saltata."""
    contact = os.environ.get("WIKIMEDIA_CONTACT", "").strip()
    return {"User-Agent": f"money-research/0.1 ({contact})"} if contact else None


# Voci Wikipedia e temi GDELT seguiti. Scelti a priori (M8), prima di qualsiasi backtest.
WIKI_ARTICLES = ["Bitcoin"]
GDELT_QUERIES = {
    # narrazione di crisi: recessione o crollo di borsa
    "crash_narrative": '(recession OR "stock market crash" OR "market crash")',
}
GDELT_START = date(2017, 1, 1)
FNG_START = date(2018, 2, 1)


def _at(d: date, days: int, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(d + timedelta(days=days), time(hh, mm), tzinfo=UTC)


# ───────────────────────── Wikipedia ─────────────────────────


def fetch_wikipedia(article: str, start: date, end: date, client: httpx.Client | None = None) -> list[tuple]:
    if client is None:
        headers = wikimedia_headers()
        if headers is None:
            return []
        client = httpx.Client(timeout=60, headers=headers)
    c = client
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
        f"{article}/daily/{start:%Y%m%d}/{end:%Y%m%d}"
    )
    r = c.get(url)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    out = []
    for it in r.json().get("items", []):
        d = datetime.strptime(it["timestamp"][:8], "%Y%m%d").date()
        out.append(("wikipedia", article, d, float(it["views"]), _at(d, 1, 6)))
    return out


# ───────────────────────── Fear & Greed ─────────────────────────


def fetch_fear_greed(client: httpx.Client | None = None) -> list[tuple]:
    c = client or httpx.Client(timeout=60, headers=UA)
    r = c.get("https://api.alternative.me/fng/", params={"limit": 0, "format": "json"})
    r.raise_for_status()
    out = []
    for it in r.json()["data"]:
        d = datetime.fromtimestamp(int(it["timestamp"]), UTC).date()
        out.append(("alternative_me", "fear_greed", d, float(it["value"]), _at(d, 0, 1)))
    return out


# ───────────────────────── GDELT ─────────────────────────


def fetch_gdelt(
    series_id: str,
    query: str,
    start: date,
    end: date,
    client: httpx.Client | None = None,
    pause: float = 6.0,
    retries: int = 6,
) -> list[tuple]:
    """Volume giornaliero (% degli articoli monitorati) a blocchi di ~3 mesi, rispettando il limite
    di GDELT (una richiesta ogni 5 secondi): pausa tra le richieste e attesa crescente se rifiutati."""
    c = client or httpx.Client(timeout=120, headers=UA)
    out = []
    a = start
    while a <= end:
        b = min(a + timedelta(days=90), end)
        params = {
            "query": query,
            "mode": "timelinevol",
            "format": "json",
            "startdatetime": f"{a:%Y%m%d}000000",
            "enddatetime": f"{b:%Y%m%d}235959",
        }
        for attempt in range(retries):
            r = c.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                break
            wait = pause * (attempt + 2)
            log.info("GDELT: limite di frequenza, attendo %.0f s", wait)
            _time.sleep(wait)
        else:
            raise RuntimeError(f"GDELT non risponde per {a}…{b}: {r.text[:200]}")
        tl = r.json().get("timeline") or []
        for p in tl[0]["data"] if tl else []:
            d = datetime.strptime(p["date"][:8], "%Y%m%d").date()
            if a <= d <= b:
                out.append(("gdelt", series_id, d, float(p["value"]), _at(d, 1, 1)))
        a = b + timedelta(days=1)
        _time.sleep(pause)
    return out


# ───────────────────────── Binance (storico BTC) ─────────────────────────


def fetch_binance_daily(symbol: str, start: date, client: httpx.Client | None = None) -> list[dict]:
    """Barre giornaliere spot dall'API pubblica di Binance (dati di mercato, nessuna chiave)."""
    c = client or httpx.Client(timeout=60, headers=UA)
    out, t = [], int(datetime.combine(start, time(0), tzinfo=UTC).timestamp() * 1000)
    while True:
        r = c.get(
            "https://data-api.binance.vision/api/v3/klines",
            params={"symbol": symbol, "interval": "1d", "startTime": t, "limit": 1000},
        )
        r.raise_for_status()
        rows = r.json()
        for k in rows:
            d = datetime.fromtimestamp(k[0] / 1000, UTC).date()
            if d >= datetime.now(UTC).date():
                continue  # barra di oggi non ancora chiusa
            out.append(
                {
                    "date": d,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "available_at": _at(d, 1, 0, 10),
                }
            )
        if len(rows) < 1000:
            return out
        t = rows[-1][0] + 86_400_000


# ───────────────────────── salvataggio ─────────────────────────


def store_series(conn: psycopg.Connection, rows: list[tuple]) -> int:
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO raw.daily_series (source, series_id, date, value, available_at)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (source, series_id, date) DO UPDATE SET value=EXCLUDED.value, ingested_at=now()""",
            rows,
        )
    return len(rows)


def store_binance(conn: psycopg.Connection, instrument: str, bars: list[dict]) -> int:
    """Salva le barre Binance come fonte 'binance' (USDT ≈ USD). Il backtest preferisce sempre la fonte
    principale (Alpaca) dove esiste e usa Binance solo per lo storico precedente."""
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO market.bar_1d (instrument_id, date, source, currency, open, high, low, close,
                                          adj_close, volume, available_at)
               VALUES (%s,%s,'binance','USD',%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (instrument_id, date, source) DO NOTHING""",
            [
                (
                    instrument,
                    b["date"],
                    b["open"],
                    b["high"],
                    b["low"],
                    b["close"],
                    b["close"],
                    b["volume"],
                    b["available_at"],
                )
                for b in bars
            ],
        )
    return len(bars)


def last_date(conn: psycopg.Connection, source: str, series_id: str) -> date | None:
    return conn.execute(
        "SELECT max(date) FROM raw.daily_series WHERE source=%s AND series_id=%s", (source, series_id)
    ).fetchone()[0]


def ingest_all(conn: psycopg.Connection, today: date) -> dict[str, int]:
    """Aggiornamento incrementale di tutte le serie (la prima volta scarica lo storico: ~5 minuti)."""
    n: dict[str, int] = {}
    for art in WIKI_ARTICLES:
        if wikimedia_headers() is None:
            log.warning("Wikipedia saltata: imposta WIKIMEDIA_CONTACT in .env (policy Wikimedia)")
            n[f"wikipedia:{art}"] = 0
            continue
        last = last_date(conn, "wikipedia", art)
        start = (last - timedelta(days=7)) if last else date(2016, 1, 1)
        n[f"wikipedia:{art}"] = store_series(conn, fetch_wikipedia(art, start, today - timedelta(days=1)))
    n["fear_greed"] = store_series(conn, fetch_fear_greed())
    for sid, q in GDELT_QUERIES.items():
        last = last_date(conn, "gdelt", sid)
        start = (last - timedelta(days=3)) if last else GDELT_START
        n[f"gdelt:{sid}"] = store_series(conn, fetch_gdelt(sid, q, start, today - timedelta(days=1)))
    last_btc = conn.execute(
        "SELECT max(date) FROM market.bar_1d WHERE instrument_id='bitcoin_etp' AND source='binance'"
    ).fetchone()[0]
    start = (last_btc + timedelta(days=1)) if last_btc else date(2017, 8, 17)
    n["binance:BTCUSDT"] = store_binance(conn, "bitcoin_etp", fetch_binance_daily("BTCUSDT", start))
    return n
