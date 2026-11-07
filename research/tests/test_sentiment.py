"""Test M8: parsing delle fonti di sentiment (senza rete) e strategie S6."""

from datetime import date

import httpx
import numpy as np
import pandas as pd

from money_research.backtest.simulator import Context
from money_research.backtest.strategies import CryptoSentimentSleeve, NarrativeRiskOff
from money_research.ingest import sentiment as S


def mock(payload, status=200):
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, json=payload)))


def test_fear_greed_e_disponibilita():
    rows = S.fetch_fear_greed(mock({"data": [{"value": "12", "timestamp": "1517443200"}]}))
    src, sid, d, v, avail = rows[0]
    assert (src, sid, d, v) == ("alternative_me", "fear_greed", date(2018, 2, 1), 12.0)
    assert avail.isoformat() == "2018-02-01T01:00:00+00:00"


def test_gdelt_tiene_solo_il_blocco_richiesto():
    payload = {
        "timeline": [{"data": [{"date": "20200101T000000Z", "value": 0.5}, {"date": "20200501T000000Z", "value": 9}]}]
    }
    rows = S.fetch_gdelt("x", "q", date(2020, 1, 1), date(2020, 1, 2), mock(payload), pause=0)
    assert [(r[2], r[3]) for r in rows] == [(date(2020, 1, 1), 0.5)]
    assert rows[0][4].isoformat() == "2020-01-02T01:00:00+00:00"  # disponibile il giorno dopo


def test_wikipedia_saltata_senza_contatto(monkeypatch):
    monkeypatch.delenv("WIKIMEDIA_CONTACT", raising=False)
    assert S.wikimedia_headers() is None
    assert S.fetch_wikipedia("Bitcoin", date(2020, 1, 1), date(2020, 1, 2)) == []
    monkeypatch.setenv("WIKIMEDIA_CONTACT", "https://example.org")
    assert "example.org" in S.wikimedia_headers()["User-Agent"]


def test_binance_scarta_la_barra_di_oggi():
    today_ms = int(pd.Timestamp.now(tz="UTC").normalize().timestamp() * 1000)
    k = lambda t, c: [t, "1", "2", "0.5", str(c), "10"]  # noqa: E731
    rows = S.fetch_binance_daily("BTCUSDT", date(2020, 1, 1), mock([k(1577836800000, 7200), k(today_ms, 1)]))
    assert [r["date"] for r in rows] == [date(2020, 1, 1)]
    assert rows[0]["available_at"].isoformat() == "2020-01-02T00:10:00+00:00"


# ───────────────────────── strategie ─────────────────────────


class View:
    def __init__(self, prices: dict[str, pd.Series], series: dict[str, pd.Series]):
        self.p, self.s = prices, series

    def history(self, i):
        return self.p[i]

    def last_close(self, i):
        return float(self.p[i].iloc[-1])

    def series(self, name):
        return self.s[name]


def flat(n=300):
    return pd.Series(np.full(n, 100.0), index=pd.bdate_range("2020-01-01", periods=n))


def ctx(view):
    return Context(date(2021, 3, 1), view, 1000.0, {}, 1000.0, "Active")


def test_fear_greed_contrarian_con_isteresi():
    s = CryptoSentimentSleeve(low=25, high=75)
    prices = {"all_world": flat(), "bitcoin_etp": flat()}
    seq = [50, 20, 60, 80, 40]  # neutro → paura (entra) → resta → euforia (esce) → resta fuori
    states = []
    for v in seq:
        w, _ = s.targets(ctx(View(prices, {"fear_greed": pd.Series([float(v)])})))
        states.append("bitcoin_etp" in w)
    assert states == [False, True, True, False, False]
    assert w["all_world"] == 0.85


def test_narrazione_esce_e_rientra():
    base = list(np.random.default_rng(0).normal(1.0, 0.1, 300))
    spike = base + [5.0] * 20  # esplosione della narrazione di crisi
    s = NarrativeRiskOff(z_off_at=2.0, z_on_at=1.0)
    prices = {"all_world": flat(), "global_bonds_hedged": flat()}
    w, _ = s.targets(ctx(View(prices, {"crash_narrative": pd.Series(base)})))
    assert w == {"all_world": 1.0}
    w, _ = s.targets(ctx(View(prices, {"crash_narrative": pd.Series(spike)})))
    assert w == {"global_bonds_hedged": 1.0}
    calm = spike + [1.0, 1.1] * 150  # calma piatta: media a 20 giorni costante, z = 0
    w, _ = s.targets(ctx(View(prices, {"crash_narrative": pd.Series(calm)})))
    assert w == {"all_world": 1.0}


def test_core_comprato_con_piano_di_accumulo():
    s = CryptoSentimentSleeve(mode="hold")
    s._targets, s._edges = {"all_world": 0.85, "bitcoin_etp": 0.14}, {"all_world": 1.0, "bitcoin_etp": 5.0}
    s._period, s._left = s._period_of(date(2021, 3, 1)), 5
    view = View({"all_world": flat(), "bitcoin_etp": flat()}, {})
    orders = s._orders(Context(date(2021, 3, 1), view, 1000.0, {}, 1000.0, "Active"))
    kinds = {o.instrument: o.kind for o in orders}
    assert kinds == {"all_world": "savings_plan", "bitcoin_etp": "regular"}
