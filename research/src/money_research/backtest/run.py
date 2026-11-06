"""Esecuzioni standard: il benchmark (piano di accumulo) e il suo report."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import psycopg

from ..config import REPO_ROOT, load_universe
from . import metrics as M
from . import registry
from .data import MarketData, load_market_data
from .report import Run, eur, num, write
from .simulator import SimConfig, Simulator
from .strategies import SavingsPlan

VALIDATION_PATH = REPO_ROOT / "config" / "validation.toml"


def load_validation(path: Path = VALIDATION_PATH) -> dict:
    v = tomllib.loads(path.read_text())
    v["research_start"] = date.fromisoformat(v["research_start"])
    v["holdout_start"] = date.fromisoformat(v["holdout_start"])
    h, m = map(int, v["decision_time"].split(":"))
    v["decision_time"] = time(h, m)
    return v


# Scenari del primo report. 50 € e 1.000 € come da piano di validazione; il PAC da 50 €/mese
# è illustrativo (altri versamenti arriveranno solo dopo la validazione).
SCENARIOS = [
    ("50 € una tantum", Decimal("50"), Decimal("0")),
    ("1.000 € una tantum", Decimal("1000"), Decimal("0")),
    ("50 € + 50 €/mese", Decimal("50"), Decimal("50")),
]


def _simulate(md: MarketData, val: dict, initial: Decimal, monthly: Decimal, k: Decimal, end: date):
    universe = {i.id: i for i in load_universe()}
    cfg = SimConfig(
        start=val["research_start"],
        end=end,
        initial_deposit_eur=initial,
        monthly_deposit_eur=monthly,
        holdout_start=val["holdout_start"],
        decision_time=val["decision_time"],
        resume_after_days=val["resume_after_days"],
        cost_multiplier=k,
    )
    strat = SavingsPlan(val["benchmark_instrument"], val["benchmark"]["expected_edge_pct"])
    return cfg, strat, Simulator(md, universe, cfg).run(strat)


def benchmark_report(conn: psycopg.Connection, out_dir: Path | None = None) -> tuple[Path, str]:
    val = load_validation()
    family = "benchmark"
    inst = val["benchmark_instrument"]
    md = load_market_data(conn, [inst], val["proxy_drag_bps_per_year"])
    # Ultimo giorno di borsa prima dell'hold-out: l'hold-out resta intatto.
    end = max(d for d in md.calendar if d < val["holdout_start"])

    def run_one(label: str, initial: Decimal, monthly: Decimal, k: Decimal) -> Run:
        cfg, strat, res = _simulate(md, val, initial, monthly, k, end)
        stats = registry.family_stats(conn, family)
        costs = float(res.totals["commissions"] + res.totals["spread"] + res.liquidation["sell_costs_eur"])
        taxes = float(res.totals["tax_withheld"] + res.totals["stamp_duty"] + res.liquidation["taxes_eur"])
        m = M.compute(
            res.daily,
            md.rf,
            final_nav=float(res.liquidation["value_eur"]),
            costs_eur=costs,
            taxes_eur=taxes,
            traded_eur=float(sum(f["notional"] for f in res.fills)),
            n_trades=len(res.fills),
            n_trials=stats.n_trials + 1,
            var_trials_sr=stats.var_sharpe_daily,
        )
        m["excess_cagr"] = 0.0  # è il benchmark: per definizione non lo batte
        conf = {k_: str(v) for k_, v in asdict(cfg).items()} | {"strategy": strat.name, "instrument": inst}
        eid, _ = registry.record(
            conn,
            family=family,
            strategy=strat.name,
            config=conf,
            data_snapshot=md.snapshot,
            period=(cfg.start, cfg.end),
            uses_holdout=False,
            metrics=m,
            notes=f"{label}, costi ×{k}",
        )
        pre = M.compute(res.daily, md.rf)
        m["cagr_pre_liquidation"] = pre["cagr"]
        m["_returns_gross"] = M.twr_returns(res.daily)
        return Run(label, res, m, eid)

    runs, sens = [], []
    for label, initial, monthly in SCENARIOS:
        base = run_one(label, initial, monthly, Decimal("1"))
        runs.append(base)
        sens.append((label, base, run_one(label, initial, monthly, Decimal("2"))))

    b = runs[0]
    years = b.metrics["years"]
    stops = [str(e["date"].year) for e in b.result.risk_events if "SoftStopTriggered" in e["event"]]
    blocked = sum(1 for x in runs[-1].result.rejections if "G-01" in x["codes"])
    findings = [
        f"Il piano di accumulo sull'ETF globale ha reso **{M_pct(b.metrics['cagr'])} l'anno netto** "
        f"in {num(years, 1)} anni ({val['research_start']} → {end}), con un drawdown massimo di "
        f"**{M_pct(b.metrics['max_drawdown'])}** e Sharpe **{num(b.metrics['sharpe'])}**.",
        f"50 € investiti sarebbero diventati **{eur(b.result.liquidation['value_eur'])}** dopo costi e tasse "
        "(liquidando tutto alla fine). Il rendimento è quello del mercato azionario globale in un periodo "
        "favorevole: non è un'aspettativa per il futuro.",
        "**Il benchmark stesso non supera le soglie del Gate 0** (Sharpe > 1, drawdown < 15%): sono soglie molto "
        "severe, che un indice azionario non rispetta. Una strategia che le supera deve battere il mercato "
        "con meno della metà del suo rischio: è raro, e un risultato del genere va guardato con sospetto.",
        "Con 50 € i costi del piano di accumulo sono quasi nulli (0 € di commissione); un ordine singolo da "
        "1 € su 50 € costerebbe il 2% e verrebbe bloccato da G-05. Raddoppiare spread e commissioni cambia "
        "pochissimo: per il benchmark contano le tasse, non i costi.",
        f"Il soft stop (G-01, −15% dal massimo) è scattato {len(stops)} volte ({', '.join(stops)}). "
        f"Con i versamenti mensili ha bloccato {blocked} acquisti durante i crolli, proprio quando comprare "
        "conveniva: è il prezzo della prudenza, da valutare prima del paper trading.",
    ]
    assumptions = [
        f"Prezzi: proxy USA `{inst}` rettificato per dividendi (come un ETF ad accumulo), convertito in EUR con "
        f"il cambio BCE e ridotto di {val['proxy_drag_bps_per_year'].get(inst)} bp/anno per ritenuta sui "
        "dividendi e TER dell'UCITS reale (stima).",
        "Decisione alle 9:00 (Roma) con i soli dati pubblicati prima (G-11); esecuzione all'apertura dello "
        "stesso giorno con metà spread stimato (10 bp per gli ETF) e 0 € di commissione (piano di accumulo).",
        "Guardrails, costi, ledger e fisco: stesso codice `money-core` del paper/live. G-10 (dati vecchi > 36 h) "
        "blocca gli ordini del lunedì e dopo i festivi USA: l'ordine si riprova il giorno dopo.",
        "Tasse: 26% al realizzo (ETF = redditi di capitale); bollo 0,2% annuo addebitato a fine anno sul valore "
        "giornaliero. 🟡 Se esistesse un **minimo di 1 €/anno** (da verificare, knowledge/fisco/08) su 50 € il "
        "bollo salirebbe al 2% l'anno.",
        "Il bollo è addebitato sulla liquidità anche se è tutta investita: la cassa può scendere di pochi "
        "centesimi sotto zero (in realtà il broker la compenserebbe).",
        "Valore 'se liquidato': vendita di tutto alla chiusura dell'ultimo giorno con 1 € di commissione e "
        "imposta del 26% sulla plusvalenza. Il CAGR netto include questa liquidazione.",
        f"Soft stop (G-01): nel backtest la ripartenza avviene dopo {val['resume_after_days']} giorni di borsa.",
        "Rendimenti time-weighted (i versamenti non sono rendimento); Sharpe con €STR (EONIA − 8,5 bp prima "
        "dell'ottobre 2019).",
    ]
    context = {
        "code_version": registry.code_version(),
        "period": (val["research_start"], end),
        "holdout": f"dal {val['holdout_start']} — **non usato** (si apre una sola volta al Gate 0)",
        "data_snapshot": md.snapshot,
        "family": family,
    }
    out_dir = out_dir or REPO_ROOT / "reports" / "validation"
    path = out_dir / f"{date.today()}-benchmark-piano-di-accumulo.md"
    sha = write(
        path,
        title="Benchmark — piano di accumulo su ETF azionario globale",
        runs=runs,
        sensitivity=sens,
        context=context,
        assumptions=assumptions,
        findings=findings,
    )
    return path, sha


def M_pct(v: float) -> str:
    return f"{v * 100:.1f}%".replace(".", ",")


# ═════════════════════════ M4: strategie ETF (S3, S4, S8) ═════════════════════════
# Griglia fissata A PRIORI (prima di vedere i risultati): ogni variante è un tentativo registrato
# nella sua famiglia (G-12) e conta nel Deflated Sharpe e nel PBO.

S3_UNIVERSE = ["world_equity", "us_equity", "em_equity", "gold", "global_bonds_hedged", "commodities", "bitcoin_etp"]
S3_CAPS = {"bitcoin_etp": 0.14}  # G-08: crypto ≤ 15% del conto
M4_CAPITALS = [Decimal("1000"), Decimal("10000"), Decimal("50")]  # 1.000 € principale, 10.000 € diagnostica


def _sectors() -> list[str]:
    return sorted(i.id for i in load_universe() if "rotation" in i.sleeves)


def m4_families() -> dict[str, list[tuple[str, Callable]]]:
    from .strategies import Combined, SectorRotation, TrendFollowing

    def s3(rebalance="monthly", vol_scaling=True):
        return TrendFollowing(
            name=f"S3 {rebalance}{' vol' if vol_scaling else ''}",
            rebalance=rebalance,
            universe=S3_UNIVERSE,
            vol_scaling=vol_scaling,
            caps=S3_CAPS,
        )

    def s4(top_k=3, hysteresis=True):
        return SectorRotation(
            name=f"S4 top{top_k}{' isteresi' if hysteresis else ''}",
            sectors=_sectors(),
            top_k=top_k,
            hysteresis=hysteresis,
        )

    return {
        "s3-tsmom": [
            ("mensile, vol scaling", lambda: s3("monthly", True)),
            ("mensile, pesi uguali", lambda: s3("monthly", False)),
            ("settimanale, vol scaling", lambda: s3("weekly", True)),
            ("settimanale, pesi uguali", lambda: s3("weekly", False)),
        ],
        "s4-rotation": [
            ("top 3, isteresi", lambda: s4(3, True)),
            ("top 3, senza isteresi", lambda: s4(3, False)),
            ("top 2, isteresi", lambda: s4(2, True)),
            ("top 2, senza isteresi", lambda: s4(2, False)),
        ],
        "s3s4-s8": [
            ("S3+S4 con regime S8", lambda: Combined(name="S3+S4+S8", trend=s3(), rotation=s4(), use_regime=True)),
            ("S3+S4 senza regime", lambda: Combined(name="S3+S4", trend=s3(), rotation=s4(), use_regime=False)),
        ],
    }


def m4_report(conn: psycopg.Connection, out_dir: Path | None = None) -> tuple[Path, str]:
    import numpy as np

    from .report import write_research

    val = load_validation()
    universe = {i.id: i for i in load_universe()}
    ids = sorted({*S3_UNIVERSE, *_sectors(), "all_world", "global_bonds_hedged"})
    md = load_market_data(conn, ids, val["proxy_drag_bps_per_year"], set(val["fx_hedged"]))
    end = max(d for d in md.calendar if d < val["holdout_start"])
    # Un anno di storia serve ai segnali: si parte dal primo giorno di borsa del 2017, anche il benchmark.
    start = min(d for d in md.calendar if d >= date(val["research_start"].year + 1, 1, 1))

    def simulate(strategy, capital: Decimal, family: str, label: str) -> Run:
        cfg = SimConfig(
            start=start,
            end=end,
            initial_deposit_eur=capital,
            holdout_start=val["holdout_start"],
            decision_time=val["decision_time"],
            resume_after_days=val["resume_after_days"],
            cash_interest=val["cash_interest"],
        )
        res = Simulator(md, universe, cfg).run(strategy)
        stats = registry.family_stats(conn, family)
        liq = float(res.liquidation["value_eur"])
        m = M.compute(
            res.daily,
            md.rf,
            final_nav=liq,
            costs_eur=float(res.totals["commissions"] + res.totals["spread"] + res.liquidation["sell_costs_eur"]),
            taxes_eur=float(res.totals["tax_withheld"] + res.totals["stamp_duty"] + res.liquidation["taxes_eur"]),
            traded_eur=float(sum(f["notional"] for f in res.fills)),
            n_trades=len(res.fills),
            n_trials=stats.n_trials + 1,
            var_trials_sr=stats.var_sharpe_daily,
        )
        conf = {k: str(v) for k, v in asdict(cfg).items()} | {"strategy": strategy.name, "variant": label}
        eid, _ = registry.record(
            conn,
            family=family,
            strategy=strategy.name,
            config=conf,
            data_snapshot=md.snapshot,
            period=(cfg.start, cfg.end),
            uses_holdout=False,
            metrics=m,
            notes=f"M4: {label}, capitale {capital} €",
        )
        m["_returns"] = M.twr_returns(res.daily, liq)
        m["_strategy_stats"] = dict(getattr(strategy, "stats", {}))
        return Run(label, res, m, eid, {"capital": capital, "family": family})

    bench = {
        cap: simulate(
            SavingsPlan(val["benchmark_instrument"], val["benchmark"]["expected_edge_pct"]),
            cap,
            "benchmark",
            "benchmark",
        )
        for cap in M4_CAPITALS
    }
    families: dict[str, list[Run]] = {}
    for family, variants in m4_families().items():
        for cap in M4_CAPITALS:
            for label, make in variants:
                run = simulate(make(), cap, family, label)
                b = bench[cap].metrics
                run.metrics["benchmark_cagr"] = b["cagr"]
                run.metrics["excess_cagr"] = run.metrics["cagr"] - b["cagr"]
                families.setdefault(family, []).append(run)

    pbo: dict[tuple[str, Decimal], float | None] = {}
    for family, runs in families.items():
        for cap in M4_CAPITALS:
            rs = [r for r in runs if r.extra["capital"] == cap]
            mat = np.column_stack([r.metrics["_returns"].to_numpy() for r in rs])
            # Varianti con rendimenti praticamente identici (es. tutte ferme in liquidità): PBO non definito.
            if np.abs(mat - mat[:, :1]).max() < 1e-6:
                pbo[(family, cap)] = None
                continue
            try:
                pbo[(family, cap)] = M.pbo(mat)
            except ValueError:
                pbo[(family, cap)] = None
    for runs in families.values():
        for r in runs:
            r.metrics["pbo"] = pbo[(r.extra["family"], r.extra["capital"])]

    out_dir = out_dir or REPO_ROOT / "reports" / "validation"
    path = out_dir / f"{date.today()}-m4-strategie-etf.md"
    sha = write_research(
        path,
        families=families,
        benchmark=bench,
        context={
            "code_version": registry.code_version(),
            "period": (start, end),
            "holdout": f"dal {val['holdout_start']} — **non usato**",
            "data_snapshot": md.snapshot,
        },
    )
    return path, sha
