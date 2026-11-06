"""Metriche di performance (3.6). Tutte al netto di costi e tasse, in EUR.

Rendimenti time-weighted: i versamenti non sono rendimento. Convenzione: il versamento arriva a
inizio giornata, quindi r_t = NAV_t / (NAV_{t-1} + versamento_t) − 1.

Deflated Sharpe Ratio: Bailey & López de Prado (2014), "The Deflated Sharpe Ratio".
PBO: Bailey, Borwein, López de Prado, Zhu (2017), "The Probability of Backtest Overfitting" (CSCV).
"""

from __future__ import annotations

import math
from itertools import combinations
from statistics import NormalDist

import numpy as np
import pandas as pd

EULER_GAMMA = 0.5772156649015329
N = NormalDist()


def twr_returns(daily: pd.DataFrame, final_nav: float | None = None) -> pd.Series:
    """Rendimenti giornalieri time-weighted. `final_nav` sostituisce l'ultimo NAV (es. valore liquidato)."""
    nav = daily["nav"].to_numpy(dtype=float).copy()
    if final_nav is not None:
        nav[-1] = final_nav
    flow = daily["flow"].to_numpy(dtype=float)
    prev = np.concatenate([[0.0], nav[:-1]])
    base = prev + flow
    r = np.where(base > 0, nav / np.where(base > 0, base, 1.0) - 1.0, 0.0)
    return pd.Series(r, index=pd.to_datetime(daily["date"]), name="r")


def rf_daily(index: pd.DatetimeIndex, rf: pd.DataFrame) -> pd.Series:
    """Tasso privo di rischio per ogni giorno (ACT/360 sui giorni di calendario trascorsi)."""
    rates = pd.merge_asof(pd.DataFrame({"date": index}), rf.sort_values("date"), on="date", allow_exact_matches=False)[
        "rate_pct"
    ].fillna(0.0)
    gaps = pd.Series(index).diff().dt.days.fillna(1).to_numpy()
    return pd.Series(rates.to_numpy() / 100 * gaps / 360, index=index)


def max_drawdown(r: pd.Series) -> float:
    idx = (1 + r).cumprod()
    return float((idx / idx.cummax() - 1).min())


def psr(sr: float, n: int, skew: float, kurt: float, sr_benchmark: float = 0.0) -> float:
    """Probabilistic Sharpe Ratio. `sr` NON annualizzato, `kurt` di Pearson (normale = 3)."""
    if n < 3:
        return float("nan")
    den = 1 - skew * sr + (kurt - 1) / 4 * sr**2
    if den <= 0:
        return float("nan")
    return N.cdf((sr - sr_benchmark) * math.sqrt(n - 1) / math.sqrt(den))


def expected_max_sharpe(n_trials: int, var_trials: float) -> float:
    """Sharpe massimo atteso per puro caso tra n_trials tentativi (soglia del DSR)."""
    if n_trials <= 1 or var_trials <= 0:
        return 0.0
    return math.sqrt(var_trials) * (
        (1 - EULER_GAMMA) * N.inv_cdf(1 - 1 / n_trials) + EULER_GAMMA * N.inv_cdf(1 - 1 / (n_trials * math.e))
    )


def deflated_sharpe(sr: float, n: int, skew: float, kurt: float, n_trials: int, var_trials: float) -> float:
    return psr(sr, n, skew, kurt, expected_max_sharpe(n_trials, var_trials))


def pbo(returns: np.ndarray, n_blocks: int = 16) -> float:
    """Probability of Backtest Overfitting con CSCV.

    returns: matrice T × M (giorni × configurazioni). Per ogni combinazione di metà dei blocchi
    come in-sample si sceglie la configurazione migliore e si guarda il suo rango out-of-sample.
    PBO = frazione delle combinazioni in cui finisce sotto la mediana.
    """
    t, m = returns.shape
    if m < 2:
        raise ValueError("il PBO richiede almeno 2 configurazioni")
    if n_blocks % 2 or t < n_blocks * 2:
        raise ValueError("servono un numero pari di blocchi e almeno 2 osservazioni per blocco")
    blocks = np.array_split(np.arange(t), n_blocks)

    def sharpe(idx: np.ndarray) -> np.ndarray:
        x = returns[idx]
        sd = x.std(axis=0, ddof=1)
        return np.where(sd > 0, x.mean(axis=0) / np.where(sd > 0, sd, 1), 0.0)

    below = total = 0
    for is_blocks in combinations(range(n_blocks), n_blocks // 2):
        is_idx = np.concatenate([blocks[b] for b in is_blocks])
        oos_idx = np.concatenate([blocks[b] for b in range(n_blocks) if b not in is_blocks])
        best = int(np.argmax(sharpe(is_idx)))
        oos = sharpe(oos_idx)
        rank = (oos < oos[best]).sum() + 1  # 1 = peggiore
        w = rank / (m + 1)
        below += math.log(w / (1 - w)) <= 0
        total += 1
    return below / total


def compute(
    daily: pd.DataFrame,
    rf: pd.DataFrame,
    *,
    final_nav: float | None = None,
    costs_eur: float = 0.0,
    taxes_eur: float = 0.0,
    traded_eur: float = 0.0,
    n_trades: int = 0,
    benchmark_r: pd.Series | None = None,
    n_trials: int = 1,
    var_trials_sr: float = 0.0,
) -> dict:
    r = twr_returns(daily, final_nav)
    ex = r - rf_daily(r.index, rf)
    days = (r.index[-1] - r.index[0]).days or 1
    years = days / 365.25
    ppy = len(r) / years  # osservazioni per anno (~252)
    growth = float((1 + r).prod())
    cagr = growth ** (1 / years) - 1
    vol = float(r.std(ddof=1) * math.sqrt(ppy))
    sd = float(ex.std(ddof=1))
    sr_d = float(ex.mean() / sd) if sd > 0 else float("nan")
    downside = float(np.sqrt((np.minimum(ex, 0) ** 2).mean()))
    mdd = max_drawdown(r)
    avg_equity = float(daily["nav"].mean())
    skew = float(ex.skew())
    kurt = float(ex.kurt()) + 3
    out = {
        "start": str(r.index[0].date()),
        "end": str(r.index[-1].date()),
        "years": years,
        "n_days": len(r),
        "total_return": growth - 1,
        "cagr": cagr,
        "volatility": vol,
        "sharpe": sr_d * math.sqrt(ppy),
        "sharpe_daily": sr_d,
        "sortino": float(ex.mean() / downside * math.sqrt(ppy)) if downside > 0 else float("nan"),
        "max_drawdown": mdd,
        "calmar": cagr / abs(mdd) if mdd < 0 else float("nan"),
        "skew": skew,
        "kurtosis": kurt,
        "n_trades": n_trades,
        "turnover_pa": traded_eur / avg_equity / years if avg_equity > 0 else float("nan"),
        "cost_drag_pa": costs_eur / avg_equity / years if avg_equity > 0 else float("nan"),
        "tax_drag_pa": taxes_eur / avg_equity / years if avg_equity > 0 else float("nan"),
        "psr": psr(sr_d, len(r), skew, kurt),
        "dsr": deflated_sharpe(sr_d, len(r), skew, kurt, n_trials, var_trials_sr),
        "n_trials": n_trials,
    }
    if benchmark_r is not None:
        b = benchmark_r.reindex(r.index).fillna(0.0)
        act = r - b
        b_years_growth = float((1 + b).prod())
        out["benchmark_cagr"] = b_years_growth ** (1 / years) - 1
        out["excess_cagr"] = cagr - out["benchmark_cagr"]
        sda = float(act.std(ddof=1))
        out["information_ratio"] = float(act.mean() / sda * math.sqrt(ppy)) if sda > 0 else float("nan")
    return out


def yearly(daily: pd.DataFrame, final_nav: float | None = None) -> pd.DataFrame:
    r = twr_returns(daily, final_nav)
    rows = []
    for y, g in r.groupby(r.index.year):
        rows.append({"anno": int(y), "rendimento": float((1 + g).prod() - 1), "max_drawdown": max_drawdown(g)})
    return pd.DataFrame(rows)
