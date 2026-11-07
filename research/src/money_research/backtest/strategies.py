"""Strategie di riferimento. Le strategie vere (M4+) implementano lo stesso protocollo."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import signals as sig
from .simulator import Context, OrderIntent


@dataclass
class SavingsPlan:
    """Benchmark (fissato a priori): tutta la liquidità nell'ETF globale con un piano di accumulo.

    Il piano di accumulo su Trade Republic non ha commissioni: ogni versamento viene investito
    appena i guardrails lo permettono (un ordine rifiutato, ad esempio per dati vecchi il lunedì
    mattina, si riprova il giorno di borsa successivo).
    """

    instrument: str
    expected_edge_pct: float
    min_order_eur: float = 1.0
    name: str = "piano-di-accumulo"
    instruments: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.instruments = [self.instrument]

    def decide(self, ctx: Context) -> list[OrderIntent]:
        if ctx.cash_eur < self.min_order_eur:
            return []
        return [
            OrderIntent(
                instrument=self.instrument,
                side="buy",
                notional_eur=ctx.cash_eur,
                kind="savings_plan",
                expected_edge_pct=self.expected_edge_pct,
                reason="investimento della liquidità (piano di accumulo)",
            )
        ]


# ═════════════════════════ strategie a pesi target (M4) ═════════════════════════

HORIZON_DAYS = 63  # orizzonte su cui si stima l'edge (3 mesi di borsa)


@dataclass
class EdgeEstimator:
    """Stima point-in-time di `expected_edge_pct` (richiesto da G-06).

    A ogni ribilanciamento si annota il livello del segnale (bucket) e il prezzo; quando sono
    passati `horizon` giorni di borsa **già disponibili**, si misura il rendimento realizzato.
    L'edge di un bucket è la media dei rendimenti realizzati, **dimezzata** (shrinkage 50%, 3.1).
    Finché le osservazioni sono meno di `min_obs` l'edge è ignoto e la strategia non compra.
    """

    horizon: int = HORIZON_DAYS
    shrink: float = 0.5
    min_obs: int = 24
    pending: list[tuple[str, str, pd.Timestamp, float]] = field(default_factory=list)
    done: dict[str, list[float]] = field(default_factory=dict)

    def record(self, instrument: str, bucket: str, hist: pd.Series) -> None:
        self.pending.append((instrument, bucket, hist.index[-1], float(hist.iloc[-1])))

    def update(self, view) -> None:
        still = []
        for inst, bucket, at, p0 in self.pending:
            h = view.history(inst)
            pos = h.index.searchsorted(at)
            if pos + self.horizon < len(h):
                self.done.setdefault(bucket, []).append(float(h.iloc[pos + self.horizon]) / p0 - 1)
            else:
                still.append((inst, bucket, at, p0))
        self.pending = still

    def edge_pct(self, bucket: str) -> float | None:
        obs = self.done.get(bucket, [])
        if len(obs) < self.min_obs:
            return None
        return self.shrink * float(np.mean(obs)) * 100


@dataclass
class TargetWeightStrategy:
    """Base: ribilancia verso pesi target con banda di non-trading (3.2) e limiti di frequenza.

    - I pesi si ricalcolano a inizio periodo (mese o settimana) e si inseguono per al massimo
      `pending_days` giorni (es. se il lunedì G-10 blocca gli ordini, si riprova il martedì).
    - Banda: si opera solo se la differenza supera `min_order_eur` (con 1 € di commissione e
      G-05 al 2%, sotto i 50 € un ordine costa troppo). Le uscite totali si fanno sempre.
    - Prima le vendite, poi gli acquisti; al massimo `max_orders_per_day` ordini (G-07).
    """

    name: str = "target-weights"
    rebalance: str = "monthly"  # "monthly" | "weekly" | "daily"
    band_pct: float = 0.0  # banda relativa: si opera solo se |Δ| > band_pct × equity (oltre ai 50 €)
    savings_plan_instruments: tuple[str, ...] = ()  # acquisti con piano di accumulo (0 € di commissione)
    min_order_eur: float = 50.0
    max_orders_per_day: int = 3
    pending_days: int = 5
    cash_buffer: float = 0.01  # liquidità di riserva per bollo e imposte (evita cassa negativa)
    instruments: list[str] = field(default_factory=list)
    _period: tuple | None = field(default=None, repr=False)
    _left: int = field(default=0, repr=False)
    _targets: dict[str, float] = field(default_factory=dict, repr=False)
    _edges: dict[str, float | None] = field(default_factory=dict, repr=False)
    stats: dict[str, int] = field(default_factory=lambda: {"no_edge": 0, "rebalances": 0}, repr=False)

    def targets(self, ctx: Context) -> tuple[dict[str, float], dict[str, float | None]]:
        raise NotImplementedError

    def _period_of(self, day) -> tuple:
        if self.rebalance == "daily":
            return (day.year, day.month, day.day)
        return (day.year, day.month) if self.rebalance == "monthly" else tuple(day.isocalendar()[:2])

    def decide(self, ctx: Context) -> list[OrderIntent]:
        period = self._period_of(ctx.day)
        if period != self._period:
            self._period, self._left = period, self.pending_days
            targets, self._edges = self.targets(ctx)
            self._targets = {i: w * (1 - self.cash_buffer) for i, w in targets.items()}
            self.stats["rebalances"] += 1
        if self._left <= 0:
            return []
        self._left -= 1
        orders = self._orders(ctx)
        if not orders:
            self._left = 0
        return orders[: self.max_orders_per_day]

    def _orders(self, ctx: Context) -> list[OrderIntent]:
        equity = ctx.equity_eur
        px = {i: ctx.view.last_close(i) for i in set(self._targets) | set(ctx.holdings)}
        values = {i: float(q) * (px[i] or 0.0) for i, q in ctx.holdings.items()}
        sells, buys = [], []
        cash = ctx.cash_eur
        band = max(self.min_order_eur, self.band_pct * equity)
        for inst, qty in ctx.holdings.items():
            t = self._targets.get(inst, 0.0)
            excess = values[inst] - t * equity
            if t == 0:
                sells.append(OrderIntent(inst, "sell", qty=qty, reason="uscita: peso target zero"))
                cash += values[inst] * 0.995 - 1
            elif excess > band and px[inst]:
                sells.append(OrderIntent(inst, "sell", notional_eur=excess, reason="riduzione verso il target"))
                cash += excess * 0.995 - 1
        deficits = sorted(
            ((t * equity - values.get(i, 0.0), i) for i, t in self._targets.items() if t > 0), reverse=True
        )
        for deficit, inst in deficits:
            if deficit <= band:
                continue
            edge = self._edges.get(inst)
            if edge is None or edge <= 0:
                self.stats["no_edge"] += 1
                continue
            notional = min(deficit, cash - 0.5)
            if notional <= self.min_order_eur:
                continue
            kind = "savings_plan" if inst in self.savings_plan_instruments else "regular"
            buys.append(
                OrderIntent(
                    inst,
                    "buy",
                    notional_eur=notional,
                    kind=kind,
                    expected_edge_pct=edge,
                    reason="acquisto verso il target",
                )
            )
            cash -= notional
        return sells + buys


@dataclass
class TrendFollowing(TargetWeightStrategy):
    """S3 — TSMOM multi-asset (Moskowitz-Ooi-Pedersen 2012) con volatility scaling."""

    universe: list[str] = field(default_factory=list)
    vol_scaling: bool = True
    vol_target: float = 0.10
    caps: dict[str, float] = field(default_factory=dict)  # es. crypto ≤ 14% (G-08: 15%)
    estimator: EdgeEstimator = field(default_factory=EdgeEstimator)

    def __post_init__(self) -> None:
        self.instruments = list(self.universe)

    def targets(self, ctx: Context):
        self.estimator.update(ctx.view)
        scores, vols = {}, {}
        for inst in self.universe:
            h = ctx.view.history(inst)
            s, v = sig.tsmom_score(h), sig.ewma_vol(h)
            if s is None or v is None or v <= 0:
                continue
            scores[inst], vols[inst] = s, v
            self.estimator.record(inst, f"s={s}", h)
        n = len(scores)
        weights = {}
        for inst, s in scores.items():
            w = s / n * (self.vol_target / vols[inst] if self.vol_scaling else 1.0)
            weights[inst] = min(w, self.caps.get(inst, 1.0))
        total = sum(weights.values())
        if total > 1:
            weights = {i: w / total for i, w in weights.items()}
        weights = {i: w for i, w in weights.items() if w > 0}
        edges = {i: self.estimator.edge_pct(f"s={scores[i]}") for i in weights}
        return weights, edges


@dataclass
class SectorRotation(TargetWeightStrategy):
    """S4 — momentum 12-1 cross-section sui settori (top K a pesi uguali) con filtro di regime."""

    sectors: list[str] = field(default_factory=list)
    regime_instrument: str = "all_world"
    safe_instrument: str = "global_bonds_hedged"
    top_k: int = 3
    hysteresis: bool = True
    keep_rank: int = 5
    estimator: EdgeEstimator = field(default_factory=EdgeEstimator)

    def __post_init__(self) -> None:
        self.instruments = [*self.sectors, self.regime_instrument, self.safe_instrument]

    def targets(self, ctx: Context):
        self.estimator.update(ctx.view)
        regime_ok = sig.above_sma(ctx.view.history(self.regime_instrument))
        if not regime_ok:  # sotto la media a 10 mesi (o storia insufficiente): rifugio
            h = ctx.view.history(self.safe_instrument)
            if len(h):
                self.estimator.record(self.safe_instrument, "safe", h)
            return {self.safe_instrument: 1.0}, {self.safe_instrument: self.estimator.edge_pct("safe")}
        moms = {}
        for inst in self.sectors:
            m = sig.momentum_12_1(ctx.view.history(inst))
            if m is not None:
                moms[inst] = m
        ranked = sorted(moms, key=moms.get, reverse=True)
        chosen: list[str] = []
        if self.hysteresis:
            chosen = [i for i in ranked[: self.keep_rank] if i in ctx.holdings][: self.top_k]
        chosen += [i for i in ranked if i not in chosen][: self.top_k - len(chosen)]
        for inst in chosen:
            self.estimator.record(inst, "top", ctx.view.history(inst))
        edge = self.estimator.edge_pct("top")
        return {i: 1 / len(chosen) for i in chosen}, {i: edge for i in chosen}


@dataclass
class Combined(TargetWeightStrategy):
    """S3 + S4 al 50% ciascuno, con l'eventuale moltiplicatore di regime S8 sull'esposizione."""

    trend: TrendFollowing | None = None
    rotation: SectorRotation | None = None
    use_regime: bool = True
    regime_instrument: str = "all_world"

    def __post_init__(self) -> None:
        self.instruments = sorted({*self.trend.instruments, *self.rotation.instruments, self.regime_instrument})

    def targets(self, ctx: Context):
        w3, e3 = self.trend.targets(ctx)
        w4, e4 = self.rotation.targets(ctx)
        k = sig.regime_multiplier(ctx.view.history(self.regime_instrument)) if self.use_regime else 1.0
        weights: dict[str, float] = {}
        for w in (w3, w4):
            for i, x in w.items():
                weights[i] = weights.get(i, 0.0) + 0.5 * x * k
        edges = {}
        for i in weights:
            known = [e for e in (e3.get(i), e4.get(i)) if e is not None]
            edges[i] = min(known) if known else None
        return weights, edges


# ═════════════════════════ M8: sentiment (S6) ═════════════════════════


@dataclass
class CryptoSentimentSleeve(TargetWeightStrategy):
    """Core 85% sull'ETF globale (piano di accumulo) + quota bitcoin al 14% (G-08: crypto ≤ 15%).

    - mode "hold": la quota crypto è sempre investita (riferimento);
    - mode "fear_greed": contrarian sul Crypto Fear & Greed Index: si entra quando l'indice scende
      a `low` o meno (paura), si esce quando sale a `high` o più (euforia); in mezzo si resta come si è.
    """

    core: str = "all_world"
    crypto: str = "bitcoin_etp"
    core_weight: float = 0.85
    crypto_weight: float = 0.14
    mode: str = "fear_greed"
    low: float = 25.0
    high: float = 75.0
    series_name: str = "fear_greed"
    estimator: EdgeEstimator = field(default_factory=EdgeEstimator)
    _in: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.instruments = [self.core, self.crypto]
        self.savings_plan_instruments = (self.core,)

    def targets(self, ctx: Context):
        self.estimator.update(ctx.view)
        if self.mode == "hold":
            self._in = True
        else:
            fg = ctx.view.series(self.series_name)
            if len(fg):
                v = float(fg.iloc[-1])
                if v <= self.low:
                    self._in = True
                elif v >= self.high:
                    self._in = False
        weights = {self.core: self.core_weight}
        h_core = ctx.view.history(self.core)
        if len(h_core):
            self.estimator.record(self.core, "core", h_core)
        edges = {self.core: self.estimator.edge_pct("core")}
        if self._in:
            h = ctx.view.history(self.crypto)
            if len(h):
                self.estimator.record(self.crypto, f"crypto:{self.mode}", h)
            weights[self.crypto] = self.crypto_weight
            edges[self.crypto] = self.estimator.edge_pct(f"crypto:{self.mode}")
        return weights, edges


@dataclass
class NarrativeRiskOff(TargetWeightStrategy):
    """ETF globale che passa alle obbligazioni quando la "narrazione di crisi" (GDELT) esplode.

    z = (media a `window` giorni del volume − media dell'ultimo anno) / deviazione standard dell'ultimo anno.
    Uscita (risk-off) se z ≥ `z_off_at`, rientro se z ≤ `z_on_at`. Con `use_sma` serve anche che l'ETF
    sia sopra la media a 10 mesi per restare investiti. mode "hold" = sempre investiti (riferimento).
    """

    risk: str = "all_world"
    safe: str = "global_bonds_hedged"
    series_name: str = "crash_narrative"
    mode: str = "narrative"
    z_off_at: float = 2.0
    z_on_at: float = 1.0
    window: int = 20
    lookback: int = 252
    use_sma: bool = False
    estimator: EdgeEstimator = field(default_factory=EdgeEstimator)
    _off: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.instruments = [self.risk, self.safe]
        self.savings_plan_instruments = (self.risk,)

    def narrative_z(self, ctx: Context) -> float | None:
        s = ctx.view.series(self.series_name)
        if len(s) < self.lookback + self.window:
            return None
        x = s.rolling(self.window).mean().dropna()
        hist = x.iloc[-self.lookback :]
        sd = float(hist.std())
        return (float(x.iloc[-1]) - float(hist.mean())) / sd if sd > 0 else 0.0

    def targets(self, ctx: Context):
        self.estimator.update(ctx.view)
        if self.mode != "hold":
            z = self.narrative_z(ctx)
            if z is not None:
                if z >= self.z_off_at:
                    self._off = True
                elif z <= self.z_on_at:
                    self._off = False
        off = self._off
        if self.use_sma and sig.above_sma(ctx.view.history(self.risk)) is False:
            off = True
        inst = self.safe if off else self.risk
        h = ctx.view.history(inst)
        if len(h):
            self.estimator.record(inst, "safe" if off else "risk", h)
        return {inst: 1.0}, {inst: self.estimator.edge_pct("safe" if off else "risk")}
