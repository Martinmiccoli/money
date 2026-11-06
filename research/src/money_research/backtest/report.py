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
