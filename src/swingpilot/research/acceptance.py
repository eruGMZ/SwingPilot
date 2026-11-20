"""Evaluador de aceptación experimental (FEAT-017; DEC-005 P11..P15, P17; REQ-G-104, REQ-G-108;
TC-ML-004, TC-ML-005, TC-ML-006).

Resultado posible: INCONCLUSIVE, REJECTED o ELIGIBLE_FOR_HUMAN_REVIEW. El evaluador nunca
devuelve APPROVED: eso solo lo decide el propietario (REQ-G-107).

- Muestra mínima: ≥ 100 trades en Train+Val, ≥ 30 en OOS y ≥ 30 en LOCKBOX (P15).
- Umbrales netos: Profit Factor ≥ 1.3, expectancy ≥ 0.10 R, drawdown ≤ 20%, Sharpe OOS ≥ 0.8
  (P11..P14). Comparación con comprar y mantener: reporte obligatorio, no filtro (P11).
- Estadística (P17): IC bootstrap 95% del expectancy OOS > 0; superar una línea base ingenua;
  corrección por número de experimentos con el Deflated Sharpe Ratio (Bailey y López de Prado,
  2014).

Fail-Closed (QA3-05, QA3-07):
- Cualquier entrada numérica no finita (NaN, ±inf) → INCONCLUSIVE.
- El evaluador calcula él mismo Sharpe, drawdown y DSR a partir de las series; no acepta
  métricas declaradas. El número de pruebas sale del registro de experimentos.
- El conteo de trades OOS declarado debe coincidir con la serie.

Dominio y coherencia (QA3R2-01) → INCONCLUSIVE si no se cumple:
- Equity estrictamente > 0 y con un punto inicial más uno por trade: len(equity) == n_trades + 1.
- Cada paso de la equity tiene el mismo signo que el trade OOS correspondiente (sube con
  ganancia, baja con pérdida, igual con 0 R): la curva debe corresponder a `oos_net_r`.
- Retornos por periodo > −1 y su producto compuesto igual al crecimiento de la equity
  (equity[-1] / equity[0], tolerancia relativa 1e-6): la serie de retornos debe cubrir la
  misma curva OOS.
- Parámetros del bootstrap enteros (n_resamples ≥ 1, block_size ≥ 1, seed ≥ 0); conteos de
  trades enteros en [0, 2^53].
- Cualquier fallo numérico del cálculo, o métrica derivada no finita (salvo Profit Factor
  infinito sin pérdidas), da INCONCLUSIVE; nunca ELIGIBLE_FOR_HUMAN_REVIEW.

No fijados por el contrato (campos obligatorios del preregistro, sin valor por defecto):
definición del Sharpe (periodos por año), línea base, parámetros del bootstrap, varianza del
Sharpe entre pruebas y umbral de probabilidad del DSR.
"""
import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np

PF_MIN, EXPECTANCY_MIN_R, DD_MAX, SHARPE_OOS_MIN = 1.3, 0.10, 0.20, 0.80
MIN_TRADES = {"train_val": 100, "oos": 30, "lockbox": 30}
_N = NormalDist()


def profit_factor(net_r: list[float]) -> float:
    gains = sum(x for x in net_r if x > 0)
    losses = -sum(x for x in net_r if x < 0)
    return math.inf if losses == 0 and gains > 0 else (gains / losses if losses else 0.0)


def expectancy(net_r: list[float]) -> float:
    return float(np.mean(net_r)) if net_r else float("nan")


def max_drawdown(equity: list[float]) -> float:
    eq = np.asarray(equity, dtype=float)
    if not len(eq):
        return 0.0
    peaks = np.maximum.accumulate(eq)
    return float(np.max((peaks - eq) / peaks))


def sharpe(returns: list[float], periods_per_year: float) -> float:
    r = np.asarray(returns, dtype=float)
    sd = r.std(ddof=1) if len(r) > 1 else 0.0
    return float(r.mean() / sd * math.sqrt(periods_per_year)) if sd > 0 else 0.0


def bootstrap_ci_mean(values: list[float], *, n_resamples: int, seed: int, alpha: float = 0.05,
                      block_size: int = 1) -> tuple[float, float]:
    """IC por percentiles del promedio. block_size > 1 → bootstrap por bloques móviles (REQ-G-106)."""
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n < 2:
        raise ValueError("se necesitan ≥ 2 observaciones")
    rng = np.random.default_rng(seed)
    b = max(1, min(block_size, n))
    n_blocks = math.ceil(n / b)
    means = np.empty(n_resamples)
    for k in range(n_resamples):
        starts = rng.integers(0, n - b + 1, size=n_blocks)
        sample = np.concatenate([x[s:s + b] for s in starts])[:n]
        means[k] = sample.mean()
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def expected_max_sharpe(trials: int, sr_variance: float) -> float:
    if trials < 2:
        return 0.0
    g = 0.5772156649015329
    return math.sqrt(sr_variance) * ((1 - g) * _N.inv_cdf(1 - 1 / trials) + g * _N.inv_cdf(1 - 1 / (trials * math.e)))


def deflated_sharpe_probability(sr: float, n_obs: int, trials: int, sr_variance: float,
                                skew: float = 0.0, kurtosis: float = 3.0) -> float:
    """P(SR verdadero > SR0), SR0 = máximo esperado por azar entre `trials` (SR por periodo)."""
    if n_obs < 2:
        return 0.0
    sr0 = expected_max_sharpe(trials, sr_variance)
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurtosis - 1) / 4 * sr ** 2))
    return _N.cdf((sr - sr0) * math.sqrt(n_obs - 1) / denom)


@dataclass(frozen=True)
class ExperimentEvidence:
    trades: dict[str, int]                 # train_val / oos / lockbox
    oos_net_r: list[float]                 # trades OOS netos en R
    oos_equity: list[float]                # curva de equity OOS (para el drawdown)
    oos_period_returns: list[float]        # retornos por periodo (para Sharpe y DSR)
    periods_per_year: float                # preregistro
    sr_variance_across_trials: float       # preregistro
    buy_and_hold_report: dict              # P11: reporte obligatorio
    baseline_beaten: bool                  # línea base del preregistro
    dsr_min_probability: float             # preregistro
    bootstrap: dict                        # {"n_resamples", "seed", "block_size"} del preregistro


@dataclass
class Verdict:
    outcome: str                           # INCONCLUSIVE | REJECTED | ELIGIBLE_FOR_HUMAN_REVIEW
    reasons: list[str]
    metrics: dict


def _finite(*values) -> bool:
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return False
        if isinstance(v, int):            # math.isfinite(int enorme) lanza OverflowError (QA3R2-01)
            continue
        if not math.isfinite(v):
            return False
    return True


_COMPOUND_RTOL = 1e-6
_MAX_COUNT = 2 ** 53                      # límite técnico: conteo exacto como float


def _domain_errors(ev: ExperimentEvidence) -> list[str]:
    """Dominio y coherencia de las series (QA3R2-01). Lista vacía = válido."""
    errs = []
    eq, net = ev.oos_equity, ev.oos_net_r
    if any(x <= 0 for x in eq):
        errs.append("equity ≤ 0")
    if len(eq) != len(net) + 1:
        errs.append(f"len(equity) = {len(eq)} ≠ trades OOS + 1 = {len(net) + 1}")
    elif not errs:
        for i, r in enumerate(net):
            step = eq[i + 1] - eq[i]
            if (step > 0) != (r > 0) or (step < 0) != (r < 0):
                errs.append(f"paso {i} de la equity ({step:+.6g}) incoherente con el trade ({r:+.6g} R)")
                break
    rets = ev.oos_period_returns
    if any(x <= -1 for x in rets):
        errs.append("retorno por periodo ≤ −100%")
    elif not errs and eq:
        growth = math.prod(1 + x for x in rets)
        target = eq[-1] / eq[0]
        if not math.isclose(growth, target, rel_tol=_COMPOUND_RTOL):
            errs.append(f"retornos compuestos ({growth:.6g}) ≠ crecimiento de la equity ({target:.6g})")
    for part, n in ev.trades.items():
        if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= _MAX_COUNT:
            errs.append(f"trades[{part!r}] = {n!r} no es entero en [0, 2^53]")
    b = ev.bootstrap
    for key, minimum in (("n_resamples", 1), ("block_size", 1), ("seed", 0)):
        val = b.get(key, 1 if key == "block_size" else None)
        if isinstance(val, bool) or not isinstance(val, int) or val < minimum:
            errs.append(f"bootstrap.{key} = {val!r} no es entero ≥ {minimum}")
    return errs


def evaluate(ev: ExperimentEvidence, registry) -> Verdict:
    if not 0 < ev.dsr_min_probability < 1:
        raise ValueError("dsr_min_probability debe venir del preregistro, en (0, 1)")
    if not ev.buy_and_hold_report:
        raise ValueError("falta la comparación con comprar y mantener (P11: reporte obligatorio)")
    if ev.trades.get("oos") != len(ev.oos_net_r):
        raise ValueError(f"trades OOS declarados ({ev.trades.get('oos')}) ≠ serie ({len(ev.oos_net_r)}) (QA3-07)")
    trials = registry.trials_count()
    metrics: dict = {"trials_count": trials, "buy_and_hold": ev.buy_and_hold_report}
    numeric = [*ev.oos_net_r, *ev.oos_equity, *ev.oos_period_returns, ev.periods_per_year,
               ev.sr_variance_across_trials, *ev.trades.values()]
    if not _finite(*numeric) or ev.periods_per_year <= 0 or ev.sr_variance_across_trials < 0 or not ev.oos_equity:
        return Verdict("INCONCLUSIVE", ["entradas no finitas, vacías o fuera de dominio (Fail-Closed)"], metrics)
    domain = _domain_errors(ev)
    if domain:
        return Verdict("INCONCLUSIVE", [f"entradas fuera de dominio o incoherentes (Fail-Closed): {e}"
                                        for e in domain], metrics)
    reasons = []
    for part, need in MIN_TRADES.items():
        if ev.trades.get(part, 0) < need:
            reasons.append(f"muestra insuficiente en {part}: {ev.trades.get(part, 0)} < {need}")
    if reasons:
        return Verdict("INCONCLUSIVE", reasons, metrics)
    try:
        r = np.asarray(ev.oos_period_returns, dtype=float)
        sr_period = float(r.mean() / r.std(ddof=1)) if len(r) > 1 and r.std(ddof=1) > 0 else 0.0
        skew = float(((r - r.mean()) ** 3).mean() / r.std(ddof=0) ** 3) if r.std(ddof=0) > 0 else 0.0
        kurt = float(((r - r.mean()) ** 4).mean() / r.std(ddof=0) ** 4) if r.std(ddof=0) > 0 else 3.0
        pf, ex = profit_factor(ev.oos_net_r), expectancy(ev.oos_net_r)
        dd = max_drawdown(ev.oos_equity)
        sh = sharpe(ev.oos_period_returns, ev.periods_per_year)
        dsr = deflated_sharpe_probability(sr_period, len(r), trials, ev.sr_variance_across_trials, skew, kurt)
        lo, hi = bootstrap_ci_mean(ev.oos_net_r, n_resamples=ev.bootstrap["n_resamples"],
                                   seed=ev.bootstrap["seed"], block_size=ev.bootstrap.get("block_size", 1))
    except (ValueError, OverflowError, MemoryError, ZeroDivisionError) as exc:   # QA3R2-01
        return Verdict("INCONCLUSIVE", [f"fallo numérico del evaluador (Fail-Closed): {exc!r}"], metrics)
    metrics.update(profit_factor=pf, expectancy_r=ex, max_drawdown=dd, sharpe_oos=sh,
                   dsr_probability=dsr, expectancy_ci95=(lo, hi))
    if not _finite(ex, dd, sh, dsr, lo, hi) or math.isnan(pf):
        return Verdict("INCONCLUSIVE", ["métrica derivada no finita (Fail-Closed)"], metrics)
    if pf < PF_MIN:
        reasons.append(f"Profit Factor {pf:.3f} < {PF_MIN}")
    if ex < EXPECTANCY_MIN_R:
        reasons.append(f"expectancy {ex:.3f} R < {EXPECTANCY_MIN_R}")
    if dd > DD_MAX:
        reasons.append(f"drawdown {dd:.1%} > {DD_MAX:.0%}")
    if sh < SHARPE_OOS_MIN:
        reasons.append(f"Sharpe OOS {sh:.3f} < {SHARPE_OOS_MIN}")
    if lo <= 0:
        reasons.append(f"IC bootstrap 95% del expectancy no es > 0 ({lo:.3f}, {hi:.3f})")
    if not ev.baseline_beaten:
        reasons.append("no supera la línea base ingenua")
    if dsr < ev.dsr_min_probability:
        reasons.append(f"Deflated Sharpe {dsr:.3f} < {ev.dsr_min_probability} con {trials} pruebas")
    if reasons:
        return Verdict("REJECTED", reasons, metrics)
    return Verdict("ELIGIBLE_FOR_HUMAN_REVIEW", [], metrics)
