"""S1 — Acquisti degli insider in cluster (docs/03-system-design/01-segnali.md §S1). Point-in-time.

Evidenza: Cohen-Malloy-Pomorski 2012 (acquisti "opportunistici" ~82 bp/mese, routinari ~0);
Lakonishok-Lee 2001 (gli acquisti predicono, le vendite no); Alldredge-Blank 2019 (cluster > 2%/mese).

Un **evento** nasce il giorno di deposito in cui, per lo stesso emittente, almeno `min_insiders` insider
non routinari hanno comprato almeno `min_value` $ ciascuno negli ultimi `window_days` giorni.
È utilizzabile dalla mattina dopo (available_at = 22:00 di New York del giorno di deposito, G-11).
"""

from __future__ import annotations

import math
from datetime import timedelta

import numpy as np
import pandas as pd

TOP_TITLES = ("chief executive", "ceo", "chief financial", "cfo", "chair", "president")


def role_weight(relationship: str | None, title: str | None) -> float:
    """CEO/CFO/Chair 1,0 · altri dirigenti e consiglieri 0,7 · azionista >10% 0,5 (3.1)."""
    t, r = (title or "").lower(), relationship or ""
    if any(k in t for k in TOP_TITLES):
        return 1.0
    if "Officer" in r or "Director" in r:
        return 0.7
    return 0.5


def classify(trades: pd.DataFrame) -> pd.Series:
    """Classe di ogni acquisto: 'routine' | 'opportunistic' | 'unclassified' (Cohen-Malloy-Pomorski).

    - routinario: l'insider ha comprato nello stesso mese di calendario in ciascuno dei 3 anni precedenti;
    - opportunistico: ha almeno 3 anni di storia (primo Form 4 ≥ 3 anni prima) e non è routinario;
    - non classificato: storia più corta.
    Usa solo operazioni passate dello stesso insider (anni precedenti): nessun dato futuro.
    """
    first = trades.groupby("owner_cik")["trans_date"].transform("min")
    p = trades[trades["trans_code"] == "P"]
    months = set(
        zip(
            p["owner_cik"],
            pd.to_datetime(p["trans_date"]).dt.year,
            pd.to_datetime(p["trans_date"]).dt.month,
            strict=True,
        )
    )
    out = pd.Series("unclassified", index=trades.index)
    td = pd.to_datetime(trades["trans_date"])
    for i, (owner, y, m, f) in enumerate(
        zip(trades["owner_cik"], td.dt.year, td.dt.month, pd.to_datetime(first), strict=True)
    ):
        if trades["trans_code"].iat[i] != "P":
            continue
        idx = trades.index[i]
        if all((owner, y - k, m) in months for k in (1, 2, 3)):
            out[idx] = "routine"
        elif td.iat[i] - f >= pd.Timedelta(days=3 * 365):
            out[idx] = "opportunistic"
    return out


def build_events(
    form4: pd.DataFrame, window_days: int = 14, min_value: float = 25_000, min_insiders: int = 2
) -> pd.DataFrame:
    """Eventi di cluster da `raw.form4` (colonne come nella tabella). Uno per emittente ogni `window_days`."""
    f = form4.copy()
    f["trans_date"] = pd.to_datetime(f["trans_date"])
    f = f.dropna(subset=["trans_date"])
    f["cls"] = classify(f)
    p = f[(f["trans_code"] == "P") & ~f["is_10b5_1"] & (f["cls"] != "routine")].copy()
    p = p[(p["shares"] > 0) & (p["price"] > 0)]
    p["value"] = p["shares"] * p["price"]
    before = (p["shares_after"] - p["shares"]).clip(lower=0)
    p["delta"] = np.where(before > 0, p["shares"] / before.replace(0, np.nan), 10.0)
    p["delta"] = p["delta"].fillna(10.0).clip(upper=10.0)
    p["w"] = [role_weight(r, t) for r, t in zip(p["relationship"], p["officer_title"], strict=True)]
    p["filing_date"] = pd.to_datetime(p["filing_date"])
    # per insider e giorno di deposito
    g = (
        p.groupby(["issuer_cik", "owner_cik", "filing_date"])
        .agg(value=("value", "sum"), delta=("delta", "max"), w=("w", "max"), symbol=("symbol", "last"),
             opp=("cls", lambda s: (s == "opportunistic").any()))
        .reset_index()
        .sort_values("filing_date")
    )  # fmt: skip
    events = []
    win = pd.Timedelta(days=window_days)
    for issuer, h in g.groupby("issuer_cik", sort=False):
        last_event = None
        dates = h["filing_date"].to_numpy()
        for d in np.unique(dates):
            d = pd.Timestamp(d)
            if last_event is not None and d - last_event <= win:
                continue
            w = h[(h["filing_date"] > d - win) & (h["filing_date"] <= d)]
            per = w.groupby("owner_cik").agg(value=("value", "sum"), delta=("delta", "max"), w=("w", "max"),
                                             opp=("opp", "max"))  # fmt: skip
            per = per[per["value"] >= min_value]
            if len(per) < min_insiders:
                continue
            last_event = d
            events.append(
                {
                    "issuer_cik": issuer,
                    "symbol": w["symbol"].dropna().iloc[-1] if w["symbol"].notna().any() else None,
                    "filing_date": d.date(),
                    "n_insiders": len(per),
                    "n_opportunistic": int(per["opp"].sum()),
                    "value": float(per["value"].sum()),
                    "delta": float(per["delta"].median()),
                    "role_weight": float(per["w"].max()),
                }
            )
    ev = pd.DataFrame(events)
    if ev.empty:
        return ev
    ev["available_at"] = [
        pd.Timestamp(d).tz_localize("America/New_York") + pd.Timedelta(hours=22) for d in ev["filing_date"]
    ]
    return ev.sort_values("available_at").reset_index(drop=True)


def score(ev: pd.DataFrame, lookback_days: int = 365) -> pd.Series:
    """z = 0,5·rank(n insider) + 0,3·rank(log valore) + 0,2·rank(Δpartecipazione), × peso del ruolo.

    I rank sono percentili rispetto agli eventi dell'ultimo anno **già pubblicati** (point-in-time).
    """
    out = np.zeros(len(ev))
    t = pd.to_datetime(ev["available_at"]).to_numpy()
    n, v, dl = ev["n_insiders"].to_numpy(), np.log(ev["value"].to_numpy()), ev["delta"].to_numpy()
    for i in range(len(ev)):
        lo = np.searchsorted(t, t[i] - np.timedelta64(lookback_days, "D"))
        sl = slice(lo, i + 1)

        def pr(x: np.ndarray, sl=sl, i=i) -> float:
            return float((x[sl] <= x[i]).mean())

        out[i] = (0.5 * pr(n) + 0.3 * pr(v) + 0.2 * pr(dl)) * ev["role_weight"].iat[i]
    return pd.Series(out, index=ev.index)


def liquidity_filter(
    ev: pd.DataFrame, bars: pd.DataFrame, min_price: float = 5.0, min_adv: float = 5e6
) -> pd.DataFrame:
    """Tiene gli eventi con prezzo ≥ 5 $ e controvalore medio a 20 giorni ≥ 5 M$, calcolati solo sulle
    barre **precedenti** al giorno di deposito. Restituisce anche il motivo degli scarti."""
    keep, reason = [], []
    by_sym = {s: g.sort_values("date") for s, g in bars.groupby("symbol")}
    for _, e in ev.iterrows():
        g = by_sym.get(e["symbol"])
        if g is None:
            keep.append(False)
            reason.append("nessun prezzo (delistato o simbolo cambiato?)")
            continue
        past = g[g["date"] < e["filing_date"]].tail(20)
        if len(past) < 20:
            keep.append(False)
            reason.append("storia insufficiente")
            continue
        adv = float((past["close"] * past["volume"]).mean())
        last = float(past["close"].iloc[-1])
        ok = last >= min_price and adv >= min_adv
        keep.append(ok)
        reason.append("" if ok else ("prezzo < 5 $" if last < min_price else "liquidità < 5 M$"))
    out = ev.copy()
    out["liquid"], out["excluded"] = keep, reason
    return out


def atr_proxy(hist: pd.Series, n: int = 20) -> float | None:
    """ATR approssimato con la media delle variazioni assolute di chiusura (non abbiamo max/min nel feed)."""
    if len(hist) < n + 1:
        return None
    return float(hist.diff().abs().iloc[-n:].mean())


def finite(x: float | None) -> bool:
    return x is not None and math.isfinite(x)


def days_between(a, b) -> int:
    return (pd.Timestamp(b) - pd.Timestamp(a)) // timedelta(days=1)
