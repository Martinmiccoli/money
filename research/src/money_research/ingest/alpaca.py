"""Client minimale per la Market Data API di Alpaca (piano Basic gratuito)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

DATA_URL = "https://data.alpaca.markets"
NEW_YORK = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


class AlpacaError(RuntimeError):
    pass


@dataclass(frozen=True)
class Bar:
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    available_at: datetime


def _stock_available_at(d: date) -> datetime:
    # Chiusura 16:00 NY + ritardo SIP di 15 min sul piano gratuito: disponibile dalle 17:00 NY (G-11).
    return datetime(d.year, d.month, d.day, 17, 0, tzinfo=NEW_YORK)


def _parse_bars(symbol: str, raw: list[dict], crypto: bool) -> list[Bar]:
    out = []
    for b in raw:
        ts = datetime.fromisoformat(b["t"].replace("Z", "+00:00"))
        if crypto:
            d = ts.date()
            avail = ts + timedelta(days=1)  # la barra copre [t, t+1g)
        else:
            d = ts.astimezone(NEW_YORK).date()
            avail = _stock_available_at(d)
        out.append(Bar(symbol, d, b["o"], b["h"], b["l"], b["c"], b.get("v", 0.0), avail))
    return out


class AlpacaData:
    def __init__(
        self,
        key_id: str = "",
        secret_key: str = "",
        feed: str = "sip",
        client: httpx.Client | None = None,
        max_retries: int = 5,
        sleep=time.sleep,
    ):
        self.feed = feed
        self._headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret_key} if key_id and secret_key else {}
        self._client = client or httpx.Client(base_url=DATA_URL, timeout=60)
        self._max_retries = max_retries
        self._sleep = sleep

    def _get(self, path: str, params: dict) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            r = self._client.get(path, params=params, headers=self._headers)
            if r.status_code == 429 and attempt < self._max_retries:
                wait = float(r.headers.get("Retry-After", 2**attempt))
                log.warning("Alpaca 429, attendo %.0fs", wait)
                self._sleep(wait)
                continue
            return r
        return r

    def _paginate(self, path: str, params: dict, crypto: bool) -> dict[str, list[Bar]]:
        out: dict[str, list[Bar]] = {}
        params = dict(params)
        while True:
            r = self._get(path, params)
            if r.status_code != 200:
                raise AlpacaError(f"{r.status_code} su {path}: {r.text[:300]}")
            body = r.json()
            for sym, bars in (body.get("bars") or {}).items():
                out.setdefault(sym, []).extend(_parse_bars(sym, bars, crypto))
            token = body.get("next_page_token")
            if not token:
                return out
            params["page_token"] = token

    def stock_bars(
        self, symbols: list[str], start: date, end: date | None = None, adjustment: str = "raw"
    ) -> dict[str, list[Bar]]:
        if not self._headers:
            raise AlpacaError("servono ALPACA_KEY_ID e ALPACA_SECRET_KEY per i dati azionari")
        params = {
            "symbols": ",".join(symbols),
            "timeframe": "1Day",
            "start": start.isoformat(),
            "adjustment": adjustment,
            "feed": self.feed,
            "limit": 10000,
        }
        if end:
            params["end"] = end.isoformat()
        try:
            return self._paginate("/v2/stocks/bars", params, crypto=False)
        except AlpacaError as e:
            if self.feed == "sip" and str(e).startswith("403"):
                log.warning("feed SIP non autorizzato, ripiego su IEX (dati di una sola borsa)")
                self.feed = "iex"
                return self.stock_bars(symbols, start, end, adjustment)
            raise

    def crypto_bars(self, symbols: list[str], start: date, end: date | None = None) -> dict[str, list[Bar]]:
        params = {"symbols": ",".join(symbols), "timeframe": "1Day", "start": start.isoformat(), "limit": 10000}
        if end:
            params["end"] = end.isoformat()
        bars = self._paginate("/v1beta3/crypto/us/bars", params, crypto=True)
        # La barra del giorno corrente non è chiusa: la scartiamo.
        today = datetime.now(tz=ZoneInfo("UTC")).date()
        return {s: [b for b in bs if b.date < today] for s, bs in bars.items()}
