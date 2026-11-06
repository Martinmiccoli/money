"""Test del simulatore e delle metriche su dati sintetici (nessun DB)."""

import math
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from money_research.backtest import metrics as M
from money_research.backtest.data import build_market_data
from money_research.backtest.simulator import (
    HoldoutError,
    OrderIntent,
    SimConfig,
    Simulator,
    guardrails_with_deposits,
    scaled_broker_toml,
)
from money_research.backtest.strategies import SavingsPlan
from money_research.config import REPO_ROOT, Instrument, Proxy

NY = ZoneInfo("America/New_York")
UNIVERSE = {
    "etf": Instrument("etf", "ETF test", "etf_ucits", "EUR", "RC", ("core",), Proxy("alpaca_stock", "ETF", "USD")),
}


def business_days(start: date, n: int) -> list[date]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def market(prices: list[float], start: date = date(2024, 1, 2), currency: str = "EUR", drag=None):
    days = business_days(start, len(prices))
    bars = pd.DataFrame(
        {
            "instrument_id": "etf",
            "date": days,
            "open": prices,
            "close": prices,
            "adj_close": prices,
            "currency": currency,
            # chiusura USA + 1h, come l'ingest reale (G-11)
            "available_at": [datetime.combine(d, time(17, 0), tzinfo=NY) for d in days],
        }
    )
    fx = pd.DataFrame({"date": [start - timedelta(days=5)], "eurusd": [1.25]})
    rf = pd.DataFrame({"series": ["ESTR"], "date": [start - timedelta(days=5)], "rate_pct": [0.0]})
    return build_market_data(bars, fx, rf, drag), days


# ───────────────────────── dati point-in-time (G-11) ─────────────────────────


def test_la_vista_non_vede_la_barra_del_giorno_stesso():
    md, days = market([100, 101, 102, 103])
    view = md.view(datetime.combine(days[2], time(9, 0), tzinfo=ZoneInfo("Europe/Rome")))
    # Alle 9:00 del terzo giorno è disponibile solo la chiusura del secondo.
    assert view.last_close("etf") == 101
    assert list(view.history("etf")) == [100, 101]
    # Il simulatore però esegue all'apertura del giorno stesso.
    assert md.open_on("etf", days[2]) == 102


def test_eta_del_dato_lunedi_mattina_supera_36_ore():
    md, days = market([100] * 6, start=date(2024, 1, 5))  # venerdì
    monday = days[1]
    assert monday.weekday() == 0
    age = md.view(datetime.combine(monday, time(9, 0), tzinfo=ZoneInfo("Europe/Rome"))).data_age_hours("etf")
    assert 57 < age < 59  # venerdì 23:00 → lunedì 9:00


def test_conversione_usd_e_drag_del_proxy():
    md, days = market([125.0, 125.0], currency="USD", drag={"etf": 100})
    s = md.series["etf"]
    assert s.close_eur[0] == pytest.approx(100.0)  # 125 USD / 1,25
    # 100 bp/anno per 1 giorno ≈ −0,0027%
    assert s.close_eur[1] == pytest.approx(100.0 * math.exp(-0.01 / 365.25))


def test_vista_senza_fuso_orario_rifiutata():
    md, days = market([100, 101])
    with pytest.raises(ValueError):
        md.view(datetime(2024, 1, 3, 9, 0))


# ───────────────────────── simulatore ─────────────────────────


def sim(prices, **kw):
    md, days = market(prices)
    cfg = SimConfig(start=days[0], end=days[-1], initial_deposit_eur=Decimal("50"), **kw)
    return Simulator(md, UNIVERSE, cfg), days


def test_piano_di_accumulo_compra_il_secondo_giorno_e_valuta():
    s, days = sim([100.0] * 5 + [110.0] * 5)
    res = s.run(SavingsPlan("etf", 4.0))
    # Primo giorno: nessun dato disponibile alle 9:00 → G-10. Si compra il giorno dopo.
    assert res.rejections[0]["codes"] == ["G-10"]
    fill = res.fills[0]
    assert fill["date"] == days[1]
    # metà spread 5 bp: fill 100,05; budget 50 € (0 € di commissione) → 0,499750 quote.
    assert fill["price"] == Decimal("100.05")
    assert fill["qty"] == Decimal("0.499750")
    assert fill["commissions"] == 0
    nav = res.daily["nav"].iloc[-1]
    assert nav == pytest.approx(0.49975 * 110 + (50 - 0.49975 * 100.05), abs=0.02)


def test_liquidazione_paga_commissione_e_tasse():
    s, days = sim([100.0] * 3 + [200.0] * 3)
    res = s.run(SavingsPlan("etf", 4.0))
    liq = res.liquidation
    qty = 0.49975
    proceeds = qty * 200 * (1 - 0.0005) - 1  # metà spread in vendita e 1 € di commissione
    gain = proceeds - qty * 100.05
    assert float(liq["taxes_eur"]) == pytest.approx(round(gain * 0.26, 2), abs=0.01)
    assert float(liq["value_eur"]) == pytest.approx(proceeds - gain * 0.26 + 50 - qty * 100.05, abs=0.03)


def test_hold_out_bloccato_senza_flag():
    md, days = market([100.0] * 10)
    cfg = SimConfig(start=days[0], end=days[-1], initial_deposit_eur=Decimal("50"), holdout_start=days[5])
    with pytest.raises(HoldoutError):
        Simulator(md, UNIVERSE, cfg)
    cfg.allow_holdout = True
    Simulator(md, UNIVERSE, cfg)  # con il flag esplicito si può


class SellEverythingDay(SavingsPlan):
    """Compra subito, poi vende tutto in un giorno preciso con un ordine normale."""

    def __init__(self, sell_on: date):
        super().__init__("etf", 4.0)
        self.sell_on = sell_on

    def decide(self, ctx):
        if ctx.day == self.sell_on and ctx.holdings:
            return [OrderIntent("etf", "sell", qty=ctx.holdings["etf"], reason="test")]
        if ctx.day < self.sell_on:
            return super().decide(ctx)
        return []


def test_vendita_in_guadagno_genera_trattenuta_del_broker():
    s, days = sim([100.0] * 3 + [150.0] * 5)
    res = s.run(SellEverythingDay(days[5]))
    sell = [f for f in res.fills if f["side"] == "sell"][0]
    assert sell["commissions"] == Decimal("1")
    assert sell["tax_withheld"] > 0
    assert res.totals["tax_withheld"] == sell["tax_withheld"]
    # dopo la vendita il conto è tutto liquidità: la liquidazione non paga altro
    assert res.liquidation["taxes_eur"] == 0


def test_guardrail_g05_blocca_un_ordine_singolo_da_50_euro():
    class OneShot(SavingsPlan):
        def decide(self, ctx):
            if ctx.cash_eur < 1:
                return []
            return [OrderIntent("etf", "buy", notional_eur=ctx.cash_eur, kind="regular", expected_edge_pct=10)]

    s, days = sim([100.0] * 5)
    res = s.run(OneShot("etf", 4.0))
    assert not res.fills
    assert any("G-05" in r["codes"] for r in res.rejections)


def test_soft_stop_sospende_e_riparte():
    prices = [100.0] * 3 + [80.0] * 30
    s, days = sim(prices, resume_after_days=5)
    res = s.run(SavingsPlan("etf", 4.0))
    kinds = [next(iter(e["event"])) for e in res.risk_events]
    assert kinds[:2] == ["SoftStopTriggered", "Resumed"]


def test_costi_x2_e_kill_switch_sui_versamenti():
    toml = scaled_broker_toml(REPO_ROOT / "config/brokers/trade_republic.toml", Decimal("2"))
    assert "fee_per_order_eur = 2.0" in toml and "etf_ucits = 20.0" in toml
    assert "ftt_it_bps = 20.0" in toml  # la tassa non si moltiplica
    g = guardrails_with_deposits((REPO_ROOT / "config/guardrails.toml").read_text(), Decimal("150"))
    assert "net_deposits_eur = 150.0" in g


# ───────────────────────── metriche ─────────────────────────


def test_twr_ignora_i_versamenti():
    # 100 € che diventano 110 (+10%), poi versamento di 100 e il totale resta 210 (0%).
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "nav": [100, 110, 210],
            "flow": [100, 0, 100],
        }
    )
    r = M.twr_returns(daily)
    assert list(np.round(r, 10)) == [0.0, 0.1, 0.0]


def test_max_drawdown():
    r = pd.Series([0.1, -0.5, 0.2])
    assert M.max_drawdown(r) == pytest.approx(-0.5)


def test_psr_e_dsr():
    # Senza tentativi multipli il DSR coincide con il PSR.
    assert M.deflated_sharpe(0.05, 1000, 0, 3, 1, 0.0) == M.psr(0.05, 1000, 0, 3)
    # PSR con rendimenti normali: z = 0,05 × √999 ≈ 1,58 → ~94%.
    assert M.psr(0.05, 1000, 0, 3) == pytest.approx(0.943, abs=0.002)
    # Con 100 tentativi la soglia sale e il DSR scende.
    assert M.deflated_sharpe(0.05, 1000, 0, 3, 100, 0.0004) < 0.5
    assert M.expected_max_sharpe(100, 0.0004) == pytest.approx(0.02 * 2.5306, abs=0.002)


def test_pbo_alto_per_il_rumore_basso_per_un_vero_vantaggio():
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.01, size=(640, 20))
    assert M.pbo(noise) > 0.3
    skilled = noise.copy()
    skilled[:, 0] += 0.004  # una configurazione con un vantaggio reale e stabile
    assert M.pbo(skilled) < 0.05
    with pytest.raises(ValueError):
        M.pbo(noise[:, :1])
