"""Simulatore event-driven giornaliero (3.6, Gate 0).

Per ogni giorno di borsa t:
1. versamenti programmati (inizio giornata);
2. la strategia decide vedendo **solo** i dati disponibili alle 9:00 di t (G-11);
3. ogni ordine passa da `money_core.check_order` (guardrails): i rifiuti si registrano;
4. esecuzione all'apertura di t con il modello di costi di `money-core` (Trade Republic);
5. tutto finisce nel ledger simulato (`money_core.Ledger`): sulle vendite il motore fiscale
   calcola l'imposta che il broker tratterrebbe (`TaxWithheld`); il bollo si addebita a fine anno;
6. valutazione alla chiusura e aggiornamento della macchina del rischio (G-01/G-02).

Costi, guardrails, ledger e fisco sono **lo stesso codice** del paper e del live.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

import money_py as mc
import pandas as pd

from ..config import REPO_ROOT, Instrument
from .data import MarketData, PointInTimeView

ROME = ZoneInfo("Europe/Rome")
QTY_STEP = Decimal("0.000001")  # frazioni fino a 6 decimali
CENT = Decimal("0.01")


class HoldoutError(RuntimeError):
    """Tentativo di usare il periodo di hold-out senza autorizzazione esplicita."""


@dataclass(frozen=True)
class OrderIntent:
    instrument: str
    side: str  # "buy" | "sell"
    notional_eur: float | None = None  # acquisti: contanti da impiegare, commissioni incluse
    qty: Decimal | None = None  # vendite: quantità (None + notional = controvalore)
    kind: str = "regular"  # "regular" | "savings_plan"
    expected_edge_pct: float | None = None
    reason: str = ""


@dataclass
class Context:
    day: date
    view: PointInTimeView
    cash_eur: float
    holdings: dict[str, Decimal]
    equity_eur: float
    risk_state: str


class Strategy(Protocol):
    name: str
    instruments: list[str]

    def decide(self, ctx: Context) -> list[OrderIntent]: ...


@dataclass
class SimConfig:
    start: date
    end: date
    initial_deposit_eur: Decimal
    monthly_deposit_eur: Decimal = Decimal("0")
    holdout_start: date | None = None
    allow_holdout: bool = False
    decision_time: time = time(9, 0)
    resume_after_days: int = 20
    cost_multiplier: Decimal = Decimal("1")
    broker_path: Path = REPO_ROOT / "config/brokers/trade_republic.toml"
    guardrails_path: Path = REPO_ROOT / "config/guardrails.toml"
    fisco_path: Path = REPO_ROOT / "config/fisco.toml"
    account: str = "backtest"


@dataclass
class SimResult:
    config: SimConfig
    strategy: str
    daily: pd.DataFrame  # date, nav, flow, cash, invested
    fills: list[dict]
    rejections: list[dict]
    risk_events: list[dict]
    records_json: str
    instruments_tax_json: str
    totals: dict[str, Decimal]
    liquidation: dict[str, Decimal]
    tax_reports: dict[int, dict] = field(default_factory=dict)


def scaled_broker_toml(path: Path, k: Decimal) -> str:
    """Profilo costi con commissioni e spread moltiplicati per k (sensitivity ×2)."""
    p = tomllib.loads(path.read_text())
    lines = [f'name = "{p["name"]}"']
    for key in ("fee_per_order_eur", "fee_savings_plan_eur", "ftt_it_bps"):
        v = Decimal(str(p[key])) * (k if key != "ftt_it_bps" else 1)
        lines.append(f"{key} = {float(v)}")
    lines.append("[spread_bps]")
    lines += [f"{c} = {float(Decimal(str(v)) * k)}" for c, v in p["spread_bps"].items()]
    return "\n".join(lines) + "\n"


def guardrails_with_deposits(text: str, net_deposits: Decimal) -> str:
    """Il kill switch G-02 si misura sul capitale versato: si aggiorna a ogni versamento."""
    new, n = re.subn(r"(?m)^net_deposits_eur\s*=.*$", f"net_deposits_eur = {float(net_deposits)}", text)
    if n != 1:
        raise ValueError("net_deposits_eur non trovato in guardrails.toml")
    return new


def _d(x: float) -> str:
    return f"{x:.6f}"


class Simulator:
    def __init__(self, data: MarketData, universe: dict[str, Instrument], cfg: SimConfig):
        if cfg.holdout_start and cfg.end >= cfg.holdout_start and not cfg.allow_holdout:
            raise HoldoutError(
                f"il periodo arriva al {cfg.end}, oltre l'inizio dell'hold-out ({cfg.holdout_start}): "
                "serve allow_holdout=True (accesso registrato, G-12)"
            )
        self.data, self.universe, self.cfg = data, universe, cfg
        self.broker = mc.BrokerProfile.from_toml(scaled_broker_toml(cfg.broker_path, cfg.cost_multiplier))
        self.rules = mc.TaxRules.load(str(cfg.fisco_path))
        self._guard_text = cfg.guardrails_path.read_text()
        self.guard = mc.GuardrailsConfig.from_toml(self._guard_text)
        self.ledger = mc.Ledger(cfg.account)
        self._n = 0

    # ───────────────────────── ledger ─────────────────────────
    def _append(self, day: date, event: dict) -> dict:
        self._n += 1
        ts = datetime.combine(day, time(12, 0), tzinfo=ROME).astimezone(ZoneInfo("UTC"))
        iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        rec = self.ledger.append(
            json.dumps(
                {
                    "event_id": f"bt-{self._n}",
                    "date": day.isoformat(),
                    "occurred_at": iso,
                    "recorded_at": iso,
                    "event": event,
                }
            )
        )
        return json.loads(rec)

    def _portfolio(self) -> dict:
        return json.loads(self.ledger.portfolio_json())

    def _holdings(self) -> dict[str, Decimal]:
        return {k: Decimal(v["qty"]) for k, v in self._portfolio()["holdings"].items()}

    # ───────────────────────── loop ─────────────────────────
    def run(self, strategy: Strategy, progress: Callable[[date], None] | None = None) -> SimResult:
        cfg = self.cfg
        days = [d for d in self.data.calendar if cfg.start <= d <= cfg.end]
        if not days:
            raise ValueError("nessun giorno di borsa nel periodo")
        instruments_tax = {i: self.universe[i].tax_category for i in strategy.instruments}
        tax_json = json.dumps(instruments_tax)
        self._tax_categories = tax_json

        rm: mc.RiskMachine | None = None
        net_deposits = Decimal("0")
        suspended_days = 0
        executed: list[date] = []
        fills, rejections, risk_events, rows = [], [], [], []
        totals = {k: Decimal("0") for k in ("commissions", "spread", "ftt", "tax_withheld", "stamp_duty", "deposits")}
        bollo_values: list[tuple[date, float]] = []
        last_month = None
        prev_day: date | None = None

        for day in days:
            if prev_day and day.year != prev_day.year:
                self._charge_stamp_duty(prev_day, bollo_values, totals)
                bollo_values = []

            # 1. versamenti
            flow = Decimal("0")
            if last_month is None:
                flow = cfg.initial_deposit_eur
            elif (day.year, day.month) != last_month and cfg.monthly_deposit_eur > 0:
                flow = cfg.monthly_deposit_eur
            last_month = (day.year, day.month)
            if flow > 0:
                self._append(day, {"kind": "Deposit", "amount_eur": str(flow)})
                net_deposits += flow
                totals["deposits"] += flow
                self.guard = mc.GuardrailsConfig.from_toml(guardrails_with_deposits(self._guard_text, net_deposits))
                if rm is None:
                    rm = mc.RiskMachine(float(flow))

            # 2. decisione con i soli dati disponibili
            decision_ts = datetime.combine(day, cfg.decision_time, tzinfo=ROME)
            view = self.data.view(decision_ts)
            pf = self._portfolio()
            holdings = {k: Decimal(v["qty"]) for k, v in pf["holdings"].items()}
            cash = float(pf["cash_eur"])
            values = {k: float(q) * (view.last_close(k) or 0.0) for k, q in holdings.items()}
            equity_view = cash + sum(values.values())
            state = rm.state() if rm else "Active"
            ctx = Context(day, view, cash, holdings, equity_view, state)
            intents = strategy.decide(ctx)

            # 3-4. guardrails ed esecuzione
            for it in intents:
                week = day.isocalendar()[:2]
                snapshot = {
                    "equity_eur": equity_view,
                    "cash_eur": float(self._portfolio()["cash_eur"]),
                    "positions": {
                        k: {"asset_class": self.universe[k].asset_class, "value_eur": v} for k, v in values.items()
                    },
                    "orders_today": sum(1 for d in executed if d == day),
                    "orders_this_week": sum(1 for d in executed if d.isocalendar()[:2] == week),
                    # Nessun dato = età enorme (finita: JSON non ammette Infinity). G-10 blocca.
                    "data_age_hours": min(
                        max([view.data_age_hours(i) for i in {it.instrument, *holdings}], default=1e9), 1e9
                    ),
                }
                res = self._execute(day, it, snapshot, state)
                if res.get("rejected"):
                    rejections.append({"date": day, "instrument": it.instrument, "side": it.side, **res})
                    continue
                executed.append(day)
                fills.append(res)
                for k in ("commissions", "spread", "ftt", "tax_withheld"):
                    totals[k] += res.get(k, Decimal("0"))

            # 6. valutazione alla chiusura e rischio
            pf = self._portfolio()
            cash = float(pf["cash_eur"])
            invested = sum(
                float(h["qty"]) * (self.data.close_on_or_before(k, day) or 0.0) for k, h in pf["holdings"].items()
            )
            nav = cash + invested
            bollo_values.append((day, invested))
            rows.append({"date": day, "nav": nav, "flow": float(flow), "cash": cash, "invested": invested})
            if rm is not None:
                ev = rm.update(self.guard, nav)
                if ev:
                    risk_events.append({"date": day, "event": json.loads(ev)})
                    self._append(
                        day,
                        {
                            "kind": "RiskStateChanged",
                            "from": state,
                            "to": rm.state(),
                            "equity_eur": str(Decimal(nav).quantize(CENT)),
                            "detail": ev,
                        },
                    )
                if rm.state() == "Suspended":
                    suspended_days += 1
                    if suspended_days >= cfg.resume_after_days:
                        risk_events.append({"date": day, "event": json.loads(rm.resume(nav))})
                        suspended_days = 0
            prev_day = day
            if progress:
                progress(day)

        self._charge_stamp_duty(prev_day, bollo_values, totals)
        daily = pd.DataFrame(rows)
        # il bollo dell'ultimo anno riduce la cassa finale
        last = self._portfolio()
        daily.loc[daily.index[-1], "cash"] = float(last["cash_eur"])
        daily.loc[daily.index[-1], "nav"] = float(last["cash_eur"]) + daily["invested"].iloc[-1]

        records = self.ledger.records_json()
        result = SimResult(
            config=cfg,
            strategy=strategy.name,
            daily=daily,
            fills=fills,
            rejections=rejections,
            risk_events=risk_events,
            records_json=records,
            instruments_tax_json=tax_json,
            totals=totals,
            liquidation=self._liquidate(records, prev_day, tax_json),
        )
        for y in sorted({d.year for d in days}):
            result.tax_reports[y] = json.loads(mc.tax_report(records, tax_json, self.rules, y))
        return result

    def _execute(self, day: date, it: OrderIntent, snapshot: dict, state: str) -> dict:
        inst = self.universe[it.instrument]
        ref = self.data.open_on(it.instrument, day)
        if ref is None:
            return {"rejected": True, "codes": ["MERCATO"], "detail": "nessuna quotazione oggi"}
        ref_s = _d(ref)
        unit = json.loads(self.broker.quote(inst.asset_class, it.side, "1", ref_s, it.kind))
        fill_px = Decimal(unit["fill_price_eur"])
        commission = Decimal(unit["commission_eur"])
        held = self._holdings().get(it.instrument, Decimal("0"))

        if it.side == "buy":
            budget = Decimal(str(it.notional_eur or 0)) - commission
            qty = (budget / fill_px).quantize(QTY_STEP, rounding=ROUND_DOWN) if budget > 0 else Decimal("0")
        else:
            qty = it.qty if it.qty is not None else Decimal(str(it.notional_eur or 0)) / Decimal(ref_s)
            qty = min(qty.quantize(QTY_STEP, rounding=ROUND_DOWN), held)
        if qty <= 0:
            return {"rejected": True, "codes": ["QTY"], "detail": "quantità nulla"}

        q = json.loads(self.broker.quote(inst.asset_class, it.side, str(qty), ref_s, it.kind))
        cost = Decimal(q["commission_eur"]) + Decimal(q["spread_cost_eur"]) + Decimal(q["ftt_eur"])
        order = {
            "instrument": it.instrument,
            "asset_class": inst.asset_class,
            "side": it.side,
            "notional_eur": float(qty * Decimal(ref_s)),
            "est_cost_eur": float(cost),
            "expected_edge_pct": it.expected_edge_pct,
            "ref_price": ref,
            "limit_price": None,
            "valid_for_hours": None,
        }
        violations = json.loads(mc.check_order(self.guard, state, json.dumps(snapshot), json.dumps(order)))
        if violations:
            return {"rejected": True, "codes": [v["code"] for v in violations], "detail": violations}

        self._append(
            day,
            {
                "kind": "Fill",
                "instrument": it.instrument,
                "side": it.side,
                "qty": str(qty),
                "price_eur": q["fill_price_eur"],
                "commission_eur": q["commission_eur"],
                "transaction_tax_eur": q["ftt_eur"],
                "ref_price_eur": ref_s,
                "venue": "sim",
            },
        )
        out = {
            "date": day,
            "instrument": it.instrument,
            "side": it.side,
            "qty": qty,
            "price": Decimal(q["fill_price_eur"]),
            "notional": qty * Decimal(q["fill_price_eur"]),
            "commissions": Decimal(q["commission_eur"]),
            "spread": Decimal(q["spread_cost_eur"]),
            "ftt": Decimal(q["ftt_eur"]),
            "reason": it.reason,
        }
        if it.side == "sell":
            tax = Decimal(mc.tax_due_for_last(self.ledger.records_json(), self._tax_categories, self.rules))
            if tax > 0:
                self._append(day, {"kind": "TaxWithheld", "amount_eur": str(tax), "reference": "sim"})
                out["tax_withheld"] = tax
        return out

    def _charge_stamp_duty(self, day: date | None, values: list[tuple[date, float]], totals: dict) -> None:
        """Bollo 0,2% annuo pro rata sul valore del dossier, giorno per giorno di calendario."""
        if day is None or not values:
            return
        daily: list[list[str]] = []
        for (d0, v), nxt in zip(values, [*values[1:], None], strict=True):
            d1 = nxt[0] if nxt else d0 + timedelta(days=1)
            for k in range((d1 - d0).days):
                daily.append([(d0 + timedelta(days=k)).isoformat(), _d(v)])
        amount = Decimal(mc.stamp_duty_estimate(self.rules, json.dumps(daily)))
        if amount > 0:
            self._append(day, {"kind": "StampDuty", "amount_eur": str(amount)})
            totals["stamp_duty"] += amount

    def _liquidate(self, records: str, day: date, tax_json: str) -> dict[str, Decimal]:
        """Valore netto se si vendesse tutto alla chiusura dell'ultimo giorno (costi e tasse inclusi)."""
        led = mc.Ledger.from_records(self.cfg.account, records)
        pf = json.loads(led.portfolio_json())
        n = self._n
        sell_costs = taxes = Decimal("0")
        for iid, h in pf["holdings"].items():
            px = self.data.close_on_or_before(iid, day)
            q = json.loads(self.broker.quote(self.universe[iid].asset_class, "sell", h["qty"], _d(px), "regular"))
            n += 1
            iso = f"{day.isoformat()}T15:00:00Z"
            led.append(
                json.dumps(
                    {
                        "event_id": f"liq-{n}",
                        "date": day.isoformat(),
                        "occurred_at": iso,
                        "recorded_at": iso,
                        "event": {
                            "kind": "Fill",
                            "instrument": iid,
                            "side": "sell",
                            "qty": h["qty"],
                            "price_eur": q["fill_price_eur"],
                            "commission_eur": q["commission_eur"],
                        },
                    }
                )
            )
            sell_costs += Decimal(q["commission_eur"]) + Decimal(q["spread_cost_eur"])
            taxes += Decimal(mc.tax_due_for_last(led.records_json(), tax_json, self.rules))
        cash = Decimal(json.loads(led.portfolio_json())["cash_eur"])
        return {
            "value_eur": (cash - taxes).quantize(CENT),
            "sell_costs_eur": sell_costs.quantize(CENT),
            "taxes_eur": taxes,
        }
