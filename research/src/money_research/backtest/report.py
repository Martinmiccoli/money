"""Report di validazione in Markdown (3.6), con grafico e hash sha256 (G-15)."""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from .metrics import yearly
from .simulator import SimResult

# Soglie del Gate 0 (docs/02-progettazione/validazione.md).
GATE0 = [
    ("Sharpe netto", "sharpe", lambda v: v > 1.0, "> 1,0"),
    ("Max drawdown", "max_drawdown", lambda v: v > -0.15, "< 15%"),
    ("Rendimento netto vs benchmark", "excess_cagr", lambda v: v > 0, "> 0"),
    ("Deflated Sharpe Ratio", "dsr", lambda v: v > 0.95, "> 95%"),
    ("Numero di trade", "n_trades", lambda v: v >= 30, "≥ 30"),
]

DISCLAIMER = (
    "Risultati simulati su dati storici: **non sono una previsione** né una promessa di rendimento. "
    "I numeri fiscali sono stime del motore e vanno verificati da un commercialista."
)


@dataclass
class Run:
    label: str
    result: SimResult
    metrics: dict
    experiment_id: int | None = None
    extra: dict = field(default_factory=dict)


def pct(v: float | None, digits: int = 1) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "n/d"
    return f"{v * 100:.{digits}f}%".replace(".", ",")


def num(v: float | None, digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "n/d"
    return f"{v:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def eur(v) -> str:
    return num(float(v)) + " €"


def gate0_rows(m: dict) -> list[str]:
    rows = []
    for name, key, ok, threshold in GATE0:
        v = m.get(key)
        if v is None:
            rows.append(f"| {name} | {threshold} | n/d | — |")
            continue
        shown = pct(v) if key in ("max_drawdown", "excess_cagr", "dsr") else num(v, 2 if key != "n_trades" else 0)
        rows.append(f"| {name} | {threshold} | {shown} | {'✅' if ok(v) else '❌'} |")
    rows.append("| PBO | < 0,5 | n/d (una sola configurazione) | — |")
    return rows


def chart(runs: list[Run], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for run in runs:
        d = run.result.daily
        x = pd.to_datetime(d["date"])
        axes[0].plot(x, d["nav"], label=f"{run.label} — valore")
        axes[0].plot(x, d["flow"].cumsum(), linestyle="--", alpha=0.6, label=f"{run.label} — versato")
        r = (1 + run.metrics["_returns_gross"]).cumprod() * 100
        axes[1].plot(r.index, r.values, label=run.label)
    axes[0].set_title("Valore del conto in EUR (netto di costi; tasse al realizzo)")
    axes[0].set_yscale("log")
    axes[1].set_title("Rendimento time-weighted (base 100), netto di costi, prima della liquidazione")
    for ax in axes:
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def write(
    path: Path,
    *,
    title: str,
    runs: list[Run],
    sensitivity: list[tuple[str, Run, Run]],
    context: dict,
    assumptions: list[str],
    findings: list[str],
) -> str:
    """Scrive il report e restituisce il suo sha256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    png = path.with_suffix(".png")
    chart(runs, png)
    L: list[str] = [f"# {title}", ""]
    L += [f"- **Generato il:** {date.today()} · **codice:** `{context['code_version']}`"]
    L += [f"- **Periodo:** {context['period'][0]} → {context['period'][1]} (periodo di ricerca)"]
    L += [f"- **Hold-out:** {context['holdout']}"]
    L += [f"- **Dati:** snapshot `{context['data_snapshot']}` · **famiglia G-12:** `{context['family']}`"]
    L += ["", f"> {DISCLAIMER}", "", "## In breve", ""] + [f"- {f}" for f in findings]

    L += ["", "## Scenari", "", f"![grafico]({png.name})", ""]
    head = "| | " + " | ".join(r.label for r in runs) + " |"
    L += [head, "|---" * (len(runs) + 1) + "|"]

    def row(name, fn):
        L.append(f"| {name} | " + " | ".join(fn(r) for r in runs) + " |")

    row("Versato", lambda r: eur(r.result.totals["deposits"]))
    row("Valore finale (tasse latenti non pagate)", lambda r: eur(r.result.daily["nav"].iloc[-1]))
    row("**Valore se liquidato** (costi e tasse inclusi)", lambda r: f"**{eur(r.result.liquidation['value_eur'])}**")
    row("**CAGR netto** (time-weighted, liquidazione inclusa)", lambda r: "**" + pct(r.metrics["cagr"]) + "**")
    row("CAGR prima delle tasse latenti", lambda r: pct(r.metrics.get("cagr_pre_liquidation")))
    row("Volatilità annua", lambda r: pct(r.metrics["volatility"]))
    row("Sharpe netto (rf = €STR)", lambda r: num(r.metrics["sharpe"]))
    row("Sortino", lambda r: num(r.metrics["sortino"]))
    row("Max drawdown", lambda r: pct(r.metrics["max_drawdown"]))
    row("Calmar", lambda r: num(r.metrics["calmar"]))
    row("Commissioni + spread", lambda r: eur(r.result.totals["commissions"] + r.result.totals["spread"]))
    row("Imposte trattenute + bollo", lambda r: eur(r.result.totals["tax_withheld"] + r.result.totals["stamp_duty"]))
    row("Imposte alla liquidazione finale", lambda r: eur(r.result.liquidation["taxes_eur"]))
    row("Ordini eseguiti", lambda r: str(len(r.result.fills)))
    row(
        "Ordini rifiutati (codice)",
        lambda r: (
            ", ".join(f"{k}×{v}" for k, v in Counter(c for x in r.result.rejections for c in x["codes"]).items()) or "—"
        ),
    )
    row("Eventi di rischio (G-01/G-02)", lambda r: str(len(r.result.risk_events)))
    row("PSR (prob. Sharpe > 0)", lambda r: pct(r.metrics["psr"]))
    row("Esperimento G-12", lambda r: f"#{r.experiment_id}" if r.experiment_id else "—")

    if sensitivity:
        L += ["", "## Sensibilità ai costi (commissioni e spread × 2)", ""]
        L += ["| Scenario | CAGR ×1 | CAGR ×2 | Liquidato ×1 | Liquidato ×2 |", "|---|---|---|---|---|"]
        for label, a, b in sensitivity:
            L.append(
                f"| {label} | {pct(a.metrics['cagr'])} | {pct(b.metrics['cagr'])} | "
                f"{eur(a.result.liquidation['value_eur'])} | {eur(b.result.liquidation['value_eur'])} |"
            )

    base = runs[0]
    L += ["", f"## Anno per anno — {base.label}", ""]
    L += ["Rendimenti al netto di costi, bollo e imposte già pagate; le imposte sulle plusvalenze non ancora "]
    L += ["realizzate sono escluse (sono nel CAGR netto qui sopra).", ""]
    L += ["| Anno | Rendimento | Max drawdown |", "|---|---|---|"]
    for _, y in yearly(base.result.daily).iterrows():
        L.append(f"| {int(y['anno'])} | {pct(y['rendimento'])} | {pct(y['max_drawdown'])} |")

    L += ["", f"## Confronto con le soglie del Gate 0 — {base.label}", ""]
    L += ["| Metrica | Soglia | Valore | Esito |", "|---|---|---|---|"] + gate0_rows(base.metrics)

    if base.result.risk_events:
        L += ["", "## Eventi di rischio", ""]
        for e in base.result.risk_events:
            L.append(f"- {e['date']}: `{e['event']}`")

    L += ["", "## Ipotesi del modello", ""] + [f"- {a}" for a in assumptions]
    L += ["", "## Registro dei tentativi (G-12)", ""]
    trials = sorted(
        [(r.experiment_id, f"{r.label}, costi ×1") for r in runs]
        + [(b.experiment_id, f"{label}, costi ×2") for label, _, b in sensitivity],
        key=lambda t: t[0] or 0,
    )
    L += [f"- #{eid} {label}" for eid, label in trials if eid]
    L += ["", "---", "", DISCLAIMER, ""]
    text = "\n".join(L)
    path.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


# ═════════════════════════ report di ricerca (M4) ═════════════════════════

FAMILY_TITLES = {
    "s3-tsmom": "S3 — Trend following multi-asset (TSMOM)",
    "s4-rotation": "S4 — Rotazione momentum sui settori",
    "s3s4-s8": "S3 + S4 con il regime S8",
}

ASSUMPTIONS_M4 = [
    "Periodo di ricerca dal primo giorno di borsa del 2017 (il 2016 serve come storia per i segnali a 12 mesi) "
    "fino all'inizio dell'hold-out, che resta intatto. Benchmark sullo stesso periodo.",
    "Proxy USA rettificati in EUR con drag annuo stimato; obbligazioni globali trattate come coperte in EUR "
    "(nessuna conversione) con 160 bp/anno di costo di copertura stimato (`config/validation.toml`).",
    "Decisione alle 9:00 con i soli dati pubblicati (G-11); controllo dei guardrails con il prezzo noto alla "
    "decisione; esecuzione all'apertura con metà spread e 1 € di commissione (ordini normali).",
    "`expected_edge_pct` (G-06): rendimento medio realizzato a 63 giorni per livello di segnale, stimato solo "
    "sul passato e **dimezzato**. Finché ci sono meno di 24 osservazioni la strategia non compra.",
    "Banda di non-trading 50 € (G-05 con 1 € di commissione), cuscinetto di liquidità 1%, massimo 3 ordini al "
    "giorno (G-07); i pesi si inseguono per 5 giorni di borsa dopo il ribilanciamento.",
    "Interessi sulla liquidità al tasso €STR quando positivo, tassati al 26%; bollo 0,2% annuo; imposte al "
    "realizzo trattenute come farebbe il broker; liquidazione finale inclusa nel CAGR netto.",
]


def _codes(run: Run, top: int = 3) -> str:
    c = Counter(code for x in run.result.rejections for code in x["codes"])
    return ", ".join(f"{k}×{v}" for k, v in c.most_common(top)) or "—"


def _best(runs: list[Run], capital) -> Run:
    rs = [r for r in runs if r.extra["capital"] == capital]
    return max(rs, key=lambda r: r.metrics["sharpe"] if math.isfinite(r.metrics["sharpe"]) else -9)


def _chart_research(families: dict[str, list[Run]], benchmark: dict, path: Path, capitals) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(capitals), figsize=(6.5 * len(capitals), 5))
    for ax, cap in zip(axes, capitals, strict=True):
        b = benchmark[cap].metrics["_returns"]
        ax.plot(b.index, (1 + b).cumprod() * 100, color="black", lw=1.5, label="benchmark (PAC)")
        for fam, runs in families.items():
            best = _best(runs, cap)
            r = best.metrics["_returns"]
            ax.plot(r.index, (1 + r).cumprod() * 100, label=f"{fam}: {best.label}")
        ax.set_title(f"Capitale {num(float(cap), 0)} € — base 100, netto (liquidazione inclusa)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def write_research(path: Path, *, families: dict[str, list[Run]], benchmark: dict, context: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    capitals = list(benchmark)
    main_cap, diag_cap = capitals[0], capitals[1]
    png = path.with_suffix(".png")
    _chart_research(families, benchmark, png, capitals[:2])

    L = ["# M4 — Strategie su ETF: trend (S3), rotazione (S4), regime (S8)", ""]
    L += [f"- **Generato il:** {date.today()} · **codice:** `{context['code_version']}`"]
    L += [f"- **Periodo:** {context['period'][0]} → {context['period'][1]} (periodo di ricerca, in-sample)"]
    L += [f"- **Hold-out:** {context['holdout']} · **dati:** `{context['data_snapshot']}`"]
    L += ["", f"> {DISCLAIMER}", ""]

    # ── In breve (generato dai numeri) ──
    L += ["## In breve", ""]
    for cap in capitals:
        b = benchmark[cap].metrics
        L.append(
            f"- **{num(float(cap), 0)} €** — benchmark: CAGR netto {pct(b['cagr'])}, Sharpe {num(b['sharpe'])}, "
            f"drawdown {pct(b['max_drawdown'])}."
        )
        for fam, runs in families.items():
            best = _best(runs, cap)
            m = best.metrics
            beats = "batte" if m["excess_cagr"] > 0 else "**non batte**"
            L.append(
                f"  - {FAMILY_TITLES[fam]} (migliore: {best.label}): CAGR {pct(m['cagr'])}, Sharpe {num(m['sharpe'])}, "
                f"drawdown {pct(m['max_drawdown'])}, {m['n_trades']} ordini — {beats} il benchmark "
                f"({pct(m['excess_cagr'])}/anno)."
            )
    passed = [
        (fam, r.label, r.extra["capital"])
        for fam, runs in families.items()
        for r in runs
        if all(ok(r.metrics.get(k)) for _, k, ok, _ in GATE0 if r.metrics.get(k) is not None)
        and (r.metrics.get("pbo") is None or r.metrics["pbo"] < 0.5)
    ]
    L.append(
        "- **Gate 0 (in-sample):** "
        + (
            "nessuna variante supera tutte le soglie."
            if not passed
            else "superano le soglie: " + "; ".join(f"{f} {lbl} ({c} €)" for f, lbl, c in passed)
        )
    )
    L += ["", f"![grafico]({png.name})", ""]

    # ── Tabelle per famiglia ──
    for fam, runs in families.items():
        L += [f"## {FAMILY_TITLES[fam]}", ""]
        L += [
            "| Variante | Capitale | Liquidato | CAGR netto | vs benchmark | Sharpe | Max DD | Ordini "
            "| Rifiuti principali | Interessi | DSR | PBO |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for cap in capitals:
            for r in [x for x in runs if x.extra["capital"] == cap]:
                m = r.metrics
                L.append(
                    f"| {r.label} | {num(float(cap), 0)} € | {eur(r.result.liquidation['value_eur'])} | "
                    f"{pct(m['cagr'])} | {pct(m['excess_cagr'])} | {num(m['sharpe'])} | {pct(m['max_drawdown'])} | "
                    f"{m['n_trades']} | {_codes(r)} | {eur(r.result.totals['interest'])} | {pct(m['dsr'])} | "
                    f"{num(m['pbo']) if m.get('pbo') is not None else 'n/d'} |"
                )
        L.append("")

    # ── Gate 0 per la migliore variante di ogni famiglia al capitale principale ──
    L += [f"## Gate 0 in-sample — migliore variante per famiglia ({num(float(main_cap), 0)} €)", ""]
    L += ["Indicativo: il Gate 0 vero si misura **una volta sola** sull'hold-out.", ""]
    for fam, runs in families.items():
        best = _best(runs, main_cap)
        L += [f"**{FAMILY_TITLES[fam]} — {best.label}**", "", "| Metrica | Soglia | Valore | Esito |"]
        L += ["|---|---|---|---|"] + gate0_rows(best.metrics)[:-1]
        pbo_v = best.metrics.get("pbo")
        L.append(
            f"| PBO | < 0,5 | {num(pbo_v) if pbo_v is not None else 'n/d'} | "
            f"{'—' if pbo_v is None else ('✅' if pbo_v < 0.5 else '❌')} |"
        )
        L.append("")

    L += [f"## Diagnostica a {num(float(diag_cap), 0)} €", ""]
    L += [
        "Con più capitale gli ordini sono più grandi, le commissioni fisse pesano meno e G-05/G-06 bloccano meno: "
        "questa colonna dice se la **strategia in sé** ha valore, al netto del vincolo dei 50 €.",
        "",
    ]
    L += ["## Ipotesi del modello", ""] + [f"- {a}" for a in ASSUMPTIONS_M4]
    L += ["", "## Registro dei tentativi (G-12)", ""]
    all_runs = [*benchmark.values(), *[r for runs in families.values() for r in runs]]
    for r in sorted(all_runs, key=lambda r: r.experiment_id or 0):
        L.append(f"- #{r.experiment_id} {r.extra.get('family', 'benchmark')}: {r.label}, {r.extra['capital']} €")
    L += ["", "---", "", DISCLAIMER, ""]
    text = "\n".join(L)
    path.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()
