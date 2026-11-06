"""Cambi di riferimento BCE (ECB Data Portal, SDMX, gratuito, senza chiave)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import httpx
import psycopg

ECB_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.{quote}.EUR.SP00.A"
# I tassi BCE sono pubblicati verso le 16:00 CET: per G-11 li consideriamo disponibili dalle 17:00.
PUBLISH_TIME = time(17, 0)
FRANKFURT = ZoneInfo("Europe/Berlin")


@dataclass(frozen=True)
class FxRate:
    pair: str
    date: date
    rate: float

    @property
    def available_at(self) -> datetime:
        return datetime.combine(self.date, PUBLISH_TIME, tzinfo=FRANKFURT)


def parse_ecb_csv(text: str, pair: str) -> list[FxRate]:
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        value = (row.get("OBS_VALUE") or "").strip()
        if not value:
            continue  # giorni senza fixing
        out.append(FxRate(pair, date.fromisoformat(row["TIME_PERIOD"]), float(value)))
    return out


def fetch_eur_rates(quote: str, start: date, client: httpx.Client | None = None) -> list[FxRate]:
    """Tassi EUR{quote}: unità di `quote` per 1 EUR."""
    c = client or httpx.Client(timeout=60)
    r = c.get(ECB_URL.format(quote=quote), params={"format": "csvdata", "startPeriod": start.isoformat()})
    if r.status_code == 404:
        return []  # nessun dato nel periodo
    r.raise_for_status()
    return parse_ecb_csv(r.text, f"EUR{quote}")


def store(conn: psycopg.Connection, rates: list[FxRate]) -> int:
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO market.fx_1d (pair, date, rate, source, available_at)
               VALUES (%s,%s,%s,'ecb',%s)
               ON CONFLICT (pair, date, source) DO UPDATE SET rate=EXCLUDED.rate, ingested_at=now()""",
            [(r.pair, r.date, r.rate, r.available_at) for r in rates],
        )
    return len(rates)


# Tassi a breve (privo di rischio per lo Sharpe). L'€STR del giorno d esce alle 8:00 di d+1;
# l'EONIA usciva la sera di d. Per prudenza li consideriamo entrambi disponibili alle 9:00 di d+1.
RATE_SERIES = {
    "ESTR": "https://data-api.ecb.europa.eu/service/data/EST/B.EU000A2X2A25.WT",
    "EONIA": "https://data-api.ecb.europa.eu/service/data/EON/D.EONIA_TO.RATE",
}
# Dal 2/10/2019 EONIA = €STR + 8,5 bp (raccomandazione BCE del 14/3/2019): la serie unica usa
# EONIA − 8,5 bp prima dell'avvio dell'€STR.
EONIA_ESTR_SPREAD_PCT = 0.085
ESTR_START = date(2019, 10, 1)


@dataclass(frozen=True)
class Rate:
    series: str
    date: date
    rate_pct: float

    @property
    def available_at(self) -> datetime:
        return datetime.combine(self.date + timedelta(days=1), time(9, 0), tzinfo=FRANKFURT)


def parse_rate_csv(text: str, series: str) -> list[Rate]:
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        value = (row.get("OBS_VALUE") or "").strip()
        if value:
            out.append(Rate(series, date.fromisoformat(row["TIME_PERIOD"]), float(value)))
    return out


def fetch_rates(series: str, start: date, client: httpx.Client | None = None) -> list[Rate]:
    c = client or httpx.Client(timeout=60)
    r = c.get(RATE_SERIES[series], params={"format": "csvdata", "startPeriod": start.isoformat()})
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return parse_rate_csv(r.text, series)


def store_rates(conn: psycopg.Connection, rates: list[Rate]) -> int:
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO market.rate_1d (series, date, rate_pct, source, available_at)
               VALUES (%s,%s,%s,'ecb',%s)
               ON CONFLICT (series, date, source) DO UPDATE SET rate_pct=EXCLUDED.rate_pct, ingested_at=now()""",
            [(r.series, r.date, r.rate_pct, r.available_at) for r in rates],
        )
    return len(rates)
