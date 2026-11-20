"""Indicadores causales (FEAT-017; REQ-G-102; TC-ML-002).

Cada valor en t usa solo datos hasta t: medias exponenciales y suavizado de Wilder recursivos,
percentiles en ventana expandida sobre el pasado. Las filas con NaN (huecos de la snapshot)
no se interpolan: el valor del indicador en esa fila es NaN y la recursión continúa con el
último valor válido (pandas `ewm(ignore_na=True)`).

Son infraestructura general: no fijan parámetros de ninguna estrategia (DEC-018).
"""
import bisect

import numpy as np
import pandas as pd


def _check_period(n: int) -> None:
    if not isinstance(n, int) or n < 1:
        raise ValueError("el periodo debe ser un entero ≥ 1")


def ema(series: pd.Series, n: int) -> pd.Series:
    _check_period(n)
    out = series.ewm(span=n, adjust=False, min_periods=n, ignore_na=True).mean()
    return out.where(series.notna())


def wilder(series: pd.Series, n: int) -> pd.Series:
    _check_period(n)
    out = series.ewm(alpha=1.0 / n, adjust=False, min_periods=n, ignore_na=True).mean()
    return out.where(series.notna())


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1, skipna=False)
    first = tr.index[0] if len(tr) else None
    if first is not None:
        tr.loc[first] = high.loc[first] - low.loc[first]
    return tr.where(high.notna() & low.notna() & close.notna())


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    return wilder(true_range(high, low, close), n)


def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    """ADX de Wilder."""
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=high.index).where(up.notna())
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=high.index).where(down.notna())
    tr_s = wilder(true_range(high, low, close), n)
    plus_di = 100 * wilder(plus_dm, n) / tr_s
    minus_di = 100 * wilder(minus_dm, n) / tr_s
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).replace([np.inf, -np.inf], np.nan)
    return wilder(dx, n)


def realized_volatility(close: pd.Series, n: int) -> pd.Series:
    """Desviación estándar de retornos logarítmicos en n periodos (sin anualizar)."""
    _check_period(n)
    r = np.log(close / close.shift(1))
    return r.rolling(n, min_periods=n).std(ddof=1)


def expanding_percentile_rank(series: pd.Series, min_periods: int) -> pd.Series:
    """Rango percentil (0..1] de x_t entre los valores válidos de x_0..x_t (solo pasado).

    Lista ordenada incremental con bisect (QA3-17): O(n log n) en comparaciones."""
    _check_period(min_periods)
    seen: list[float] = []
    out = []
    for x in series.to_numpy(dtype=float):
        if np.isnan(x):
            out.append(np.nan)
            continue
        bisect.insort(seen, x)
        n = len(seen)
        out.append(np.nan if n < min_periods else bisect.bisect_right(seen, x) / n)
    return pd.Series(out, index=series.index)
