"""Cambi di riferimento BCE (ECB Data Portal, SDMX, gratuito, senza chiave)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, time
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
