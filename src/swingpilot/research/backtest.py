"""Backtest con el modelo de ejecución preregistrado (FEAT-017; REQ-G-109, REQ-G-142;
DEC-013 aclaración 2; DEC-004 P03/P04; INV-005, INV-009; TC-ML-018).

Reglas:
- Señal sobre vela cerrada i → entrada a la apertura de la vela i+1, con slippage adverso y
  comisión (sin look-ahead). Si la vela i+1 es un hueco (NaN), la señal se descarta.
- Stop tocado dentro de la vela → precio del stop con slippage 0.10% adverso.
- Hueco (apertura ≤ stop) → apertura con slippage adverso. Mismo criterio para el take-profit.
- Vela que toca stop y take-profit → se asume el stop primero.
- Comisión: max(real, 0.10%) por lado sobre el nocional (REQ-G-P03).
- Velas NaN: no hay ejecuciones ni actualizaciones en ese periodo; la posición sigue abierta.
- Trailing stop: solo puede subir (INV-009); el nuevo stop rige desde la vela siguiente.
- Long-only y una posición a la vez (INV-003, INV-005).
- Resultados en R con bruto, costos y neto por separado (REQ-G-142). El bruto usa precios de
  referencia sin fricciones (apertura, stop, TP); los costos son comisión + slippage, cada uno
  por separado (QA3-12). R se mide sobre el riesgo real: precio de entrada ejecutado − stop
  inicial.
- La lógica de estrategia solo recibe las velas hasta la actual inclusive (QA3-11): no puede
  ver el futuro.
- Señales inválidas (stop no finito, ≤ 0 o ≥ precio de entrada ejecutado; TP no finito o ≤
  precio de entrada) se descartan y se cuentan (QA3-12).

El motor no contiene ninguna estrategia: recibe la lógica por interfaz (DEC-018: el piloto no
se preregistra todavía).
"""
import math
import numbers
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import pandas as pd

MIN_COMMISSION = 0.001   # 0.10% por lado (DEC-004 P03)
SLIPPAGE = 0.001         # 0.10% (DEC-004 P04)


@dataclass(frozen=True)
class EntrySignal:
    stop_price: float
    take_profit: float | None = None


@dataclass(frozen=True)
class ExecutionModel:
    commission_rate: float = MIN_COMMISSION
    slippage: float = SLIPPAGE

    def __post_init__(self):
        # QA3R2-06: solo números reales finitos, no booleanos, con 0.001 ≤ valor < 1.0. Una
        # comparación con NaN es siempre falsa y True vale 1, así que sin esta comprobación
        # pasarían el mínimo; un valor ≥ 1.0 daría precios de ejecución ≤ 0.
        for name in ("commission_rate", "slippage"):
            v = getattr(self, name)
            if isinstance(v, (bool, np.bool_)) or not isinstance(v, numbers.Real):
                raise ValueError(f"{name} debe ser un número real no booleano (QA3R2-06)")
            try:
                finite = math.isfinite(v)
            except OverflowError:   # entero demasiado grande para float
                finite = False
            if not finite:
                raise ValueError(f"{name} debe ser finito (QA3R2-06)")
            if v >= 1.0:
                raise ValueError(f"{name} debe ser menor que 1.0 (QA3R2-06)")
        if self.commission_rate < MIN_COMMISSION:
            raise ValueError("la comisión no puede ser menor que 0.10% por lado (REQ-G-P03)")
        if self.slippage < SLIPPAGE:
            raise ValueError("el slippage no puede ser menor que 0.10% (REQ-G-P04)")


class StrategyLogic(Protocol):
    def entry_signal(self, bars: pd.DataFrame, i: int) -> EntrySignal | None: ...
    def exit_signal(self, bars: pd.DataFrame, i: int, position: "Position") -> bool: ...
    def trailing_stop(self, bars: pd.DataFrame, i: int, position: "Position") -> float | None: ...


@dataclass
class Position:
    entry_index: int
    entry_time: int
    entry_price: float
    initial_stop: float
    stop: float
    take_profit: float | None
    stop_history: list[tuple[int, float]] = field(default_factory=list)


@dataclass
class Trade:
    entry_time: int
    exit_time: int
    entry_price: float               # ejecutado (con slippage)
    exit_price: float                # ejecutado (con slippage)
    initial_stop: float
    exit_reason: str                 # STOP | STOP_GAP | TAKE_PROFIT | TAKE_PROFIT_GAP | EXIT_SIGNAL | END_OF_DATA
    gross_r: float                   # con precios de referencia, sin fricciones
    slippage_r: float
    commission_r: float

    @property
    def cost_r(self) -> float:
        return self.slippage_r + self.commission_r

    @property
    def net_r(self) -> float:
        return self.gross_r - self.cost_r


@dataclass
class BacktestResult:
    trades: list[Trade]
    skipped_signals: int
    invalid_signals: int = 0

    def summary(self) -> dict:
        g = sum(t.gross_r for t in self.trades)
        sl = sum(t.slippage_r for t in self.trades)
        cm = sum(t.commission_r for t in self.trades)
        return {"trades": len(self.trades), "gross_r": g, "slippage_r": sl, "commission_r": cm,
                "costs_r": sl + cm, "net_r": g - sl - cm, "skipped_signals": self.skipped_signals,
                "invalid_signals": self.invalid_signals}

    def equity_curve(self, risk_fraction: float, start: float = 1.0) -> list[float]:
        """Equity con riesgo fijo por operación (fracción preregistrada; INV-001 ≤ 1.5%)."""
        if not 0 < risk_fraction <= 0.015:
            raise ValueError("risk_fraction debe estar en (0, 0.015] (INV-001)")
        eq = [start]
        for t in self.trades:
            eq.append(eq[-1] * (1 + risk_fraction * t.net_r))
        return eq


def _valid(row) -> bool:
    return not any(np.isnan(row[k]) for k in ("open", "high", "low", "close"))


def _finite_pos(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and np.isfinite(x) and x > 0


def run_backtest(bars: pd.DataFrame, logic: StrategyLogic, model: ExecutionModel = ExecutionModel()) -> BacktestResult:
    """`bars`: una temporalidad, ordenada por open_time, columnas open/high/low/close/open_time."""
    if not bars["open_time"].is_monotonic_increasing:
        raise ValueError("las velas deben estar ordenadas por open_time")
    bars = bars.reset_index(drop=True)
    rows = bars.to_dict("records")
    s, fee = model.slippage, model.commission_rate
    trades: list[Trade] = []
    pos: Position | None = None
    entry_ref = 0.0
    pending_entry: EntrySignal | None = None
    pending_exit = False
    skipped = invalid = 0

    def close(i, ref_price, reason):
        nonlocal pos
        fill = ref_price * (1 - s)
        risk = pos.entry_price - pos.initial_stop
        gross = (ref_price - entry_ref) / risk
        slip = ((pos.entry_price - entry_ref) + (ref_price - fill)) / risk
        comm = fee * (pos.entry_price + fill) / risk
        trades.append(Trade(pos.entry_time, rows[i]["open_time"], pos.entry_price, fill,
                            pos.initial_stop, reason, gross, slip, comm))
        pos = None

    for i, row in enumerate(rows):
        valid = _valid(row)
        # 1) órdenes decididas al cierre de la vela anterior, a la apertura de esta
        if pending_entry is not None:
            sig, pending_entry = pending_entry, None
            if not valid:
                skipped += 1
            else:
                fill = row["open"] * (1 + s)
                tp = sig.take_profit
                if not _finite_pos(sig.stop_price) or sig.stop_price >= fill or \
                        (tp is not None and (not _finite_pos(tp) or tp <= fill)):
                    invalid += 1   # QA3-12: señal inválida respecto de la entrada ejecutada
                else:
                    entry_ref = row["open"]
                    pos = Position(i, row["open_time"], fill, sig.stop_price, sig.stop_price, tp)
        if pending_exit and pos is not None and valid:
            pending_exit = False
            close(i, row["open"], "EXIT_SIGNAL")
        if not valid:
            continue
        # 2) stop / take-profit dentro de la vela (stop primero)
        if pos is not None:
            o, h, lo = row["open"], row["high"], row["low"]
            tp = pos.take_profit
            if o <= pos.stop:
                close(i, o, "STOP_GAP")
            elif lo <= pos.stop:
                close(i, pos.stop, "STOP")
            elif tp is not None and o >= tp:
                close(i, o, "TAKE_PROFIT_GAP")
            elif tp is not None and h >= tp:
                close(i, tp, "TAKE_PROFIT")
        # 3) decisiones al cierre de esta vela (rigen desde la siguiente); la lógica solo ve
        #    las velas hasta i inclusive (QA3-11)
        visible = bars.iloc[: i + 1]
        if pos is not None:
            new_stop = logic.trailing_stop(visible, i, pos)
            if new_stop is not None and _finite_pos(new_stop) and new_stop > pos.stop:   # INV-009
                pos.stop = new_stop
                pos.stop_history.append((i, new_stop))
            if logic.exit_signal(visible, i, pos):
                pending_exit = True
        elif pending_entry is None:
            sig = logic.entry_signal(visible, i)
            if sig is not None:
                pending_entry = sig
    if pos is not None:
        last = max(k for k, r in enumerate(rows) if _valid(r))
        close(last, rows[last]["close"], "END_OF_DATA")
    return BacktestResult(trades, skipped, invalid)
