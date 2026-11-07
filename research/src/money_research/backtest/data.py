"""Dati di mercato per il backtest, con accesso point-in-time (G-11).

La strategia non tocca mai il DataFrame completo: riceve una `PointInTimeView` che restituisce
solo le barre con `available_at` **precedente** all'istante della decisione. Il simulatore, invece,
usa il prezzo di apertura del giorno per eseguire gli ordini (è un fatto, non un input della decisione).

Prezzi: si usano i proxy USA rettificati (dividendi reinvestiti, come un ETF ad accumulo),
convertiti in EUR con il cambio BCE e ridotti di un costo annuo stimato (`proxy_drag_bps_per_year`).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime

import numpy as np
import pandas as pd
import psycopg

from ..ingest.ecb import EONIA_ESTR_SPREAD_PCT, ESTR_START


@dataclass
class Series:
    """Serie di un singolo strumento, ordinata per data."""

    dates: np.ndarray  # datetime64[D]
    open_eur: np.ndarray
    close_eur: np.ndarray
    available_at: np.ndarray  # datetime64[ns] UTC

    def __post_init__(self) -> None:
        self._by_date = {pd.Timestamp(d).date(): i for i, d in enumerate(self.dates)}

    def index_on(self, day: date) -> int | None:
        return self._by_date.get(day)

    def last_available_index(self, ts: datetime) -> int:
        """Indice dell'ultima barra con available_at < ts (-1 se nessuna)."""
        t = np.datetime64(pd.Timestamp(ts).tz_convert("UTC").tz_localize(None), "ns")
        return int(np.searchsorted(self.available_at, t, side="left")) - 1


@dataclass
class DailySeries:
    """Serie non di prezzo (sentiment, attenzione) con la sua disponibilità (G-11)."""

    dates: np.ndarray  # datetime64[D]
    values: np.ndarray
    available_at: np.ndarray  # datetime64[ns] UTC


@dataclass
class MarketData:
    series: dict[str, Series]
    rf: pd.DataFrame  # colonne: date, rate_pct (serie unica €STR / EONIA − 8,5 bp)
    snapshot: str = ""  # hash dei dati usati (riproducibilità, G-12)
    calendar: list[date] = field(default_factory=list)
    extra: dict[str, DailySeries] = field(default_factory=dict)

    def view(self, decision_ts: datetime) -> PointInTimeView:
        return PointInTimeView(self, decision_ts)

    def open_on(self, instrument: str, day: date) -> float | None:
        s = self.series.get(instrument)
        i = s.index_on(day) if s else None
        return None if i is None else float(s.open_eur[i])

    def close_on_or_before(self, instrument: str, day: date) -> float | None:
        s = self.series.get(instrument)
        if s is None:
            return None
        i = int(np.searchsorted(s.dates, np.datetime64(day, "D"), side="right")) - 1
        return None if i < 0 else float(s.close_eur[i])


class PointInTimeView:
    """Quello che la strategia può vedere all'istante della decisione. Niente futuro."""

    def __init__(self, data: MarketData, decision_ts: datetime):
        if decision_ts.tzinfo is None:
            raise ValueError("decision_ts deve avere il fuso orario")
        self._data = data
        self.decision_ts = decision_ts

    def _idx(self, instrument: str) -> tuple[Series, int]:
        s = self._data.series[instrument]
        return s, s.last_available_index(self.decision_ts)

    def last_close(self, instrument: str) -> float | None:
        s, i = self._idx(instrument)
        return None if i < 0 else float(s.close_eur[i])

    def history(self, instrument: str) -> pd.Series:
        """Chiusure in EUR fino all'ultima disponibile (indice: data)."""
        s, i = self._idx(instrument)
        return pd.Series(s.close_eur[: i + 1], index=pd.to_datetime(s.dates[: i + 1]), name=instrument)

    def series(self, name: str) -> pd.Series:
        """Serie di sentiment/attenzione con i soli valori pubblicati prima della decisione."""
        s = self._data.extra[name]
        t = np.datetime64(pd.Timestamp(self.decision_ts).tz_convert("UTC").tz_localize(None), "ns")
        mask = s.available_at < t
        return pd.Series(s.values[mask], index=pd.to_datetime(s.dates[mask]), name=name)

    def data_age_hours(self, instrument: str) -> float:
        """Età del dato più recente disponibile (infinita se non c'è nulla): alimenta G-10."""
        s, i = self._idx(instrument)
        if i < 0:
            return float("inf")
        avail = pd.Timestamp(s.available_at[i]).tz_localize("UTC")
        return (pd.Timestamp(self.decision_ts) - avail).total_seconds() / 3600


def _drag_factor(dates: pd.Series, bps_per_year: float) -> np.ndarray:
    years = (dates - dates.iloc[0]).dt.days.to_numpy() / 365.25
    return np.exp(-bps_per_year / 10_000 * years)


def build_market_data(
    bars: pd.DataFrame,
    fx: pd.DataFrame,
    rf: pd.DataFrame,
    drag_bps: dict[str, float] | None = None,
    fx_hedged: set[str] | frozenset[str] = frozenset(),
) -> MarketData:
    """Costruisce i dati da DataFrame grezzi.

    bars: instrument_id, date, open, close, adj_close, currency, available_at
    fx:   date, eurusd            rf: series, date, rate_pct
    fx_hedged: strumenti coperti in EUR (il prezzo del proxy non si converte con il cambio).
    """
    drag_bps = drag_bps or {}
    bars = bars.copy()
    bars["date"] = pd.to_datetime(bars["date"])
    fx = fx.copy()
    fx["date"] = pd.to_datetime(fx["date"])
    bars = pd.merge_asof(bars.sort_values("date"), fx.sort_values("date"), on="date")
    usd = (bars["currency"] == "USD") & ~bars["instrument_id"].isin(list(fx_hedged))
    if usd.any() and bars.loc[usd, "eurusd"].isna().any():
        raise ValueError("cambio EURUSD mancante all'inizio del periodo: esegui `money ingest fx`")
    to_eur = np.where(usd, 1.0 / bars["eurusd"].to_numpy(), 1.0)
    adj = (bars["adj_close"].fillna(bars["close"]) / bars["close"]).to_numpy()
    bars["open_eur"] = bars["open"].to_numpy() * adj * to_eur
    bars["close_eur"] = bars["close"].to_numpy() * adj * to_eur

    series: dict[str, Series] = {}
    for iid, g in bars.groupby("instrument_id", sort=True):
        g = g.sort_values("date").reset_index(drop=True)
        k = _drag_factor(g["date"], drag_bps.get(iid, drag_bps.get("default", 0.0)))
        series[iid] = Series(
            dates=g["date"].to_numpy().astype("datetime64[D]"),
            open_eur=g["open_eur"].to_numpy() * k,
            close_eur=g["close_eur"].to_numpy() * k,
            available_at=pd.to_datetime(g["available_at"], utc=True).dt.tz_localize(None).to_numpy(),
        )

    rf = rf.copy()
    rf["date"] = pd.to_datetime(rf["date"])
    estr = rf[rf["series"] == "ESTR"][["date", "rate_pct"]]
    eonia = rf[(rf["series"] == "EONIA") & (rf["date"] < pd.Timestamp(ESTR_START))][["date", "rate_pct"]]
    eonia = eonia.assign(rate_pct=eonia["rate_pct"] - EONIA_ESTR_SPREAD_PCT)
    rf_all = pd.concat([eonia, estr]).sort_values("date").reset_index(drop=True)

    h = hashlib.sha256()
    for iid in sorted(series):
        s = series[iid]
        h.update(iid.encode())
        h.update(np.round(s.close_eur, 8).tobytes())
        h.update(s.dates.astype("int64").tobytes())
    # Solo giorni feriali: le crypto quotano anche nel weekend, ma il conto opera in settimana.
    calendar = sorted({pd.Timestamp(d).date() for s in series.values() for d in s.dates})
    calendar = [d for d in calendar if d.weekday() < 5]
    return MarketData(series=series, rf=rf_all, snapshot=h.hexdigest()[:16], calendar=calendar)


def load_market_data(
    conn: psycopg.Connection,
    instruments: list[str],
    drag_bps: dict[str, float] | None = None,
    fx_hedged: set[str] | frozenset[str] = frozenset(),
    extra: list[tuple[str, str]] | None = None,
) -> MarketData:
    bars = pd.DataFrame(
        conn.execute(
            # Una barra per giorno: si preferisce la fonte principale (Alpaca); le altre (es. Binance)
            # servono solo a coprire lo storico precedente.
            """SELECT DISTINCT ON (instrument_id, date)
                      instrument_id, date, open, close, adj_close, currency, available_at
               FROM market.bar_1d WHERE instrument_id = ANY(%s)
               ORDER BY instrument_id, date, (source = 'alpaca') DESC, source""",
            (instruments,),
        ).fetchall(),
        columns=["instrument_id", "date", "open", "close", "adj_close", "currency", "available_at"],
    )
    missing = set(instruments) - set(bars["instrument_id"])
    if missing:
        raise ValueError(f"nessuna barra per {sorted(missing)}: esegui `money ingest all`")
    fx = pd.DataFrame(
        conn.execute("SELECT date, rate FROM market.fx_1d WHERE pair='EURUSD' ORDER BY date").fetchall(),
        columns=["date", "eurusd"],
    )
    rf = pd.DataFrame(
        conn.execute("SELECT series, date, rate_pct FROM market.rate_1d ORDER BY date").fetchall(),
        columns=["series", "date", "rate_pct"],
    )
    md = build_market_data(bars, fx, rf, drag_bps, fx_hedged)
    for source, series_id in extra or []:
        md.extra[series_id] = load_daily_series(conn, source, series_id)
    return md


def load_daily_series(conn: psycopg.Connection, source: str, series_id: str) -> DailySeries:
    rows = conn.execute(
        "SELECT date, value, available_at FROM raw.daily_series WHERE source=%s AND series_id=%s ORDER BY date",
        (source, series_id),
    ).fetchall()
    if not rows:
        raise ValueError(f"serie {source}/{series_id} vuota: esegui `money ingest sentiment`")
    return DailySeries(
        dates=np.array([r[0] for r in rows], dtype="datetime64[D]"),
        values=np.array([r[1] for r in rows], dtype=float),
        available_at=pd.to_datetime([r[2] for r in rows], utc=True).tz_localize(None).to_numpy(),
    )
