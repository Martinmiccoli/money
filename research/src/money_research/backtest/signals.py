"""Segnali S3 (trend), S4 (rotazione) e S8 (regime): funzioni pure sulla storia dei prezzi.

Ricevono solo la storia **già disponibile** (da `PointInTimeView.history`), quindi non possono
guardare nel futuro. Parametri di partenza dalla letteratura (docs/03-system-design/01-segnali.md).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

MONTH = 21  # giorni di borsa
YEAR = 252


def _ret(p: np.ndarray, back: int, skip: int = 0) -> float:
    return float(p[-1 - skip] / p[-1 - back] - 1)


def tsmom_score(hist: pd.Series) -> float | None:
    """S3 — Moskowitz-Ooi-Pedersen: media dei segni dei rendimenti a 1, 3, 6 e 12-1 mesi.

    Solo long (G-03): ogni orizzonte positivo vale 0,25, quindi s ∈ {0; 0,25; 0,5; 0,75; 1}.
    None se la storia è più corta di un anno.
    """
    p = hist.to_numpy(dtype=float)
    if len(p) < YEAR + 1:
        return None
    rets = [_ret(p, MONTH), _ret(p, 3 * MONTH), _ret(p, 6 * MONTH), _ret(p, YEAR, skip=MONTH)]
    return sum(r > 0 for r in rets) / 4


def ewma_vol(hist: pd.Series, span: int = 60) -> float | None:
    """Volatilità annualizzata EWMA dei rendimenti logaritmici (span 60 giorni).

    L'annualizzazione usa il numero effettivo di osservazioni per anno: le crypto quotano 7 giorni su 7.
    """
    if len(hist) < span + 1:
        return None
    r = np.log(hist.astype(float)).diff().dropna()
    var = float((r**2).ewm(span=span).mean().iloc[-1])
    last_year = hist.index[hist.index > hist.index[-1] - pd.Timedelta(days=365)]
    per_year = max(len(last_year), 1)
    return math.sqrt(var * per_year)


def momentum_12_1(hist: pd.Series) -> float | None:
    """S4 — rendimento da 12 mesi fa a 1 mese fa (Jegadeesh-Titman)."""
    p = hist.to_numpy(dtype=float)
    if len(p) < YEAR + 1:
        return None
    return _ret(p, YEAR, skip=MONTH)


def above_sma(hist: pd.Series, months: int = 10) -> bool | None:
    """Prezzo sopra la media mobile a `months` mesi (filtro di regime, Faber 2007)."""
    n = months * MONTH
    if len(hist) < n:
        return None
    return float(hist.iloc[-1]) > float(hist.iloc[-n:].mean())


def vol_calm(hist: pd.Series) -> bool | None:
    """Volatilità realizzata a 20 giorni sotto la sua mediana dell'ultimo anno."""
    if len(hist) < YEAR + 21:
        return None
    r = np.log(hist.astype(float)).diff()
    v20 = r.rolling(20).std()
    return float(v20.iloc[-1]) < float(v20.iloc[-YEAR:].median())


def regime_multiplier(hist: pd.Series) -> float:
    """S8 — moltiplicatore di esposizione ∈ {1; 0,5; 0,25} sull'azionario globale.

    Un punto se il prezzo è sopra la media a 10 mesi, uno se la volatilità è calma.
    Senza storia sufficiente si resta prudenti (0,5).
    """
    a, c = above_sma(hist), vol_calm(hist)
    if a is None or c is None:
        return 0.5
    return {2: 1.0, 1: 0.5, 0: 0.25}[int(a) + int(c)]
