"""Test dei segnali S3/S4/S8 e della logica di ribilanciamento (nessun DB)."""

from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from money_research.backtest import signals as sig
from money_research.backtest.simulator import Context
from money_research.backtest.strategies import EdgeEstimator, SectorRotation, TargetWeightStrategy


def series(values, start="2020-01-01") -> pd.Series:
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def trend(n=300, daily=0.001):
    return series(100 * np.exp(daily * np.arange(n)))


class FakeView:
    def __init__(self, data: dict[str, pd.Series], upto: int | None = None):
        self.data, self.upto = data, upto

    def history(self, inst):
        h = self.data[inst]
        return h if self.upto is None else h.iloc[: self.upto]

    def last_close(self, inst):
        h = self.history(inst)
        return float(h.iloc[-1]) if len(h) else None


def ctx(view, cash=1000.0, holdings=None, equity=None, day=date(2021, 3, 1)):
    holdings = holdings or {}
    eq = equity if equity is not None else cash + sum(float(q) * view.last_close(i) for i, q in holdings.items())
    return Context(day, view, cash, holdings, eq, "Active")


# ───────────────────────── segnali ─────────────────────────


def test_tsmom_rialzo_ribasso_e_storia_corta():
    assert sig.tsmom_score(trend(300, 0.001)) == 1.0
    assert sig.tsmom_score(trend(300, -0.001)) == 0.0
    assert sig.tsmom_score(trend(100)) is None


def test_tsmom_misto():
    # Sale per un anno, scende del 3% nell'ultimo mese: 12-1, 6 e 3 mesi positivi, 1 mese negativo.
    up = 100 * np.exp(0.001 * np.arange(280))
    down = up[-1] * np.exp(-0.0015 * np.arange(1, 22))
    assert sig.tsmom_score(series(np.concatenate([up, down]))) == 0.75


def test_volatilita_ewma():
    # EWMA "RiskMetrics": non sottrae la media, quindi un trend perfetto ha vol = |r| · √252.
    assert sig.ewma_vol(trend(300)) == pytest.approx(0.001 * np.sqrt(252), rel=0.02)
    rng = np.random.default_rng(1)
    noisy = series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400))))
    assert sig.ewma_vol(noisy) == pytest.approx(0.01 * np.sqrt(252), rel=0.25)


def test_momentum_e_regime():
    assert sig.momentum_12_1(trend(300, 0.001)) == pytest.approx(np.exp(0.001 * 231) - 1, rel=1e-6)
    assert sig.above_sma(trend(300, 0.001)) is True
    assert sig.above_sma(trend(300, -0.001)) is False
    assert sig.regime_multiplier(trend(100)) == 0.5  # storia insufficiente: prudenza
    assert sig.regime_multiplier(trend(300, -0.001)) in (0.25, 0.5)


# ───────────────────────── stima dell'edge ─────────────────────────


def test_edge_solo_dal_passato_e_dimezzato():
    h = trend(400, 0.001)
    est = EdgeEstimator(horizon=63, min_obs=2)
    est.record("x", "b", h.iloc[:200])
    est.record("x", "b", h.iloc[:250])
    est.update(FakeView({"x": h}, upto=263))  # la prima ha 63 giorni dopo (barra 262), la seconda no
    assert len(est.done.get("b", [])) == 1 and est.edge_pct("b") is None
    est.update(FakeView({"x": h}, upto=400))
    assert est.edge_pct("b") == pytest.approx(0.5 * (np.exp(0.063) - 1) * 100, rel=1e-6)


# ───────────────────────── ribilanciamento ─────────────────────────


class Fixed(TargetWeightStrategy):
    def __init__(self, targets, edges, **kw):
        super().__init__(**kw)
        self._t, self._e = targets, edges

    def targets(self, c):
        return self._t, self._e


def test_prima_le_vendite_poi_gli_acquisti_e_banda():
    view = FakeView({"a": series([100.0]), "b": series([100.0]), "c": series([100.0])})
    s = Fixed({"b": 0.5, "c": 0.02}, {"b": 2.0, "c": 2.0}, cash_buffer=0.0)
    orders = s.decide(ctx(view, cash=500.0, holdings={"a": Decimal("5")}))
    # vende tutta "a" (target 0), compra "b"; "c" (20 €) è sotto la banda di 50 €
    assert [(o.instrument, o.side) for o in orders] == [("a", "sell"), ("b", "buy")]
    assert orders[1].notional_eur == pytest.approx(500.0)


def test_senza_edge_non_compra_e_limite_ordini():
    data = {k: series([100.0]) for k in "abcde"}
    s = Fixed({k: 0.2 for k in "abcde"}, {"a": None, "b": -1.0, "c": 1, "d": 1, "e": 1}, cash_buffer=0.0)
    orders = s.decide(ctx(FakeView(data), cash=1000.0))
    assert {o.instrument for o in orders} <= {"c", "d", "e"}
    assert len(orders) == 3 and s.stats["no_edge"] == 2


def test_rotazione_con_isteresi_tiene_chi_resta_nei_primi_5():
    # 6 settori con momentum crescente: s5 è il migliore, s0 il peggiore.
    data = {f"s{i}": trend(300, 0.0002 * (i + 1)) for i in range(6)}
    data["all_world"] = trend(300, 0.001)
    data["safe"] = trend(300, 0.0)
    view = FakeView(data)
    rot = SectorRotation(sectors=[f"s{i}" for i in range(6)], safe_instrument="safe", top_k=3)
    held = {"s1": Decimal("1")}  # 5° per momentum: con isteresi resta
    w, _ = rot.targets(ctx(view, holdings=held))
    assert set(w) == {"s1", "s5", "s4"}
    rot_no = SectorRotation(sectors=[f"s{i}" for i in range(6)], safe_instrument="safe", top_k=3, hysteresis=False)
    w2, _ = rot_no.targets(ctx(view, holdings=held))
    assert set(w2) == {"s5", "s4", "s3"}


def test_rotazione_va_sul_rifugio_in_regime_negativo():
    data = {f"s{i}": trend(300, 0.001) for i in range(3)}
    data["all_world"] = trend(300, -0.001)
    data["safe"] = trend(300, 0.0)
    rot = SectorRotation(sectors=["s0", "s1", "s2"], safe_instrument="safe")
    w, _ = rot.targets(ctx(FakeView(data)))
    assert w == {"safe": 1.0}
