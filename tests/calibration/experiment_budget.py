"""Tope incremental de la experimentación de IMPL-2 (DEC-016 Q38). Herramienta de desarrollo.

- USD 1.00 como máximo para TODA la experimentación de IMPL-2 (libro propio, persistente).
- Aviso único al 80% ($0.80); bloqueo al alcanzar el tope.
- Reserva atómica: antes de cada llamada se reserva su costo máximo posible bajo un candado;
  la llamada solo se envía si cabe en este tope Y en el tope mensual de $5 del AIBudget real
  (REQ-G-096), que se sigue usando y registrando.
- Un solo proceso a la vez (candado de archivo exclusivo): dos corridas simultáneas no pueden
  reservar contra el mismo saldo.
- Si el costo real no se puede medir, se registra el máximo reservado (conservador) y se
  relanza el error, igual que AIBudget.settle.

Interfaz compatible con la que usa AIProviderAdapter: try_reserve / release / settle, y
cap_reached / can_call para EntryGate.
"""
import fcntl
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from swingpilot.ai.budget import AIBudget, call_cost_usd

EXPERIMENT_CAP_USD = 1.00
EXPERIMENT_WARN_FRACTION = 0.80

_DDL = """
CREATE TABLE IF NOT EXISTS experiment_usage (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, recorded_at_utc TEXT NOT NULL, run_label TEXT NOT NULL,
    agent TEXT NOT NULL, model TEXT NOT NULL, input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL, cost_usd REAL NOT NULL, estimated INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS experiment_warnings (
    threshold_usd REAL PRIMARY KEY, sent_at_utc TEXT NOT NULL, spent_usd REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS experiment_usage_no_update BEFORE UPDATE ON experiment_usage
BEGIN SELECT RAISE(ABORT, 'experiment_usage es inmutable'); END;
CREATE TRIGGER IF NOT EXISTS experiment_usage_no_delete BEFORE DELETE ON experiment_usage
BEGIN SELECT RAISE(ABORT, 'experiment_usage es inmutable'); END;
"""


class ExperimentBudgetLocked(RuntimeError):
    """Otro proceso tiene abierto el libro de la experimentación."""


def _warn_stderr(spent: float, threshold: float, cap: float) -> None:
    print(f"[IMPL-2] AVISO: gasto de experimentación ${spent:.6f} ≥ {threshold:.2f} "
          f"(80% del tope de ${cap:.2f})", file=sys.stderr)


class ExperimentBudget:
    def __init__(self, inner: AIBudget, path: str | Path, *, run_label: str = "",
                 cap: float = EXPERIMENT_CAP_USD, warn_fraction: float = EXPERIMENT_WARN_FRACTION,
                 on_warning: Callable[[float, float, float], None] = _warn_stderr,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        path = Path(path)
        self._lockfile = open(path.with_suffix(".lock"), "w")
        try:
            fcntl.flock(self._lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            self._lockfile.close()
            raise ExperimentBudgetLocked(str(path)) from e
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.executescript(_DDL)
        self._inner, self._label = inner, run_label
        self.cap, self.warn_at = cap, round(cap * warn_fraction, 6)
        self._on_warning, self._now = on_warning, now
        self._lock = threading.RLock()
        self._inflight: dict[int, tuple[float, int, str, int, int]] = {}
        self._next = 0
        self.warnings: list[float] = []  # avisos emitidos en este proceso

    def close(self) -> None:
        self._db.close()
        fcntl.flock(self._lockfile, fcntl.LOCK_UN)
        self._lockfile.close()

    # ---- consulta ----
    def spent(self) -> float:
        with self._lock:
            return float(self._db.execute(
                "SELECT COALESCE(SUM(cost_usd),0) FROM experiment_usage").fetchone()[0])

    def remaining(self) -> float:
        return max(0.0, self.cap - self.spent())

    def cap_reached(self) -> bool:
        return self.spent() >= self.cap or self._inner.cap_reached()

    def can_call(self) -> bool:
        return not self.cap_reached()

    def spent_this_month(self) -> float:  # para quien espera la interfaz de AIBudget
        return self._inner.spent_this_month()

    # ---- reserva / liquidación ----
    def try_reserve(self, model: str, max_input_tokens: int, max_output_tokens: int) -> int | None:
        est = call_cost_usd(model, max_input_tokens, max_output_tokens)
        with self._lock:
            committed = self.spent() + sum(r[0] for r in self._inflight.values())
            if committed + est > self.cap:
                return None  # bloqueo: no cabe en el tope de IMPL-2
            irid = self._inner.try_reserve(model, max_input_tokens, max_output_tokens)
            if irid is None:
                return None  # no cabe en el tope mensual
            self._next += 1
            self._inflight[self._next] = (est, irid, model, max_input_tokens, max_output_tokens)
            return self._next

    def release(self, rid: int) -> None:
        with self._lock:
            r = self._inflight.pop(rid, None)
        if r is not None:
            self._inner.release(r[1])

    def settle(self, rid: int, agent: str, model: str | None, input_tokens: int | None,
               output_tokens: int | None) -> float:
        with self._lock:
            r = self._inflight.get(rid)
        if r is None:
            raise KeyError(f"reserva desconocida: {rid}")
        est, irid, rmodel, rin, rout = r
        try:
            try:
                cost = self._inner.settle(irid, agent, model, input_tokens, output_tokens)
            except (KeyError, ValueError):
                self._insert(agent, rmodel, rin, rout, est, estimated=True)
                raise
            self._insert(agent, model, input_tokens, output_tokens, cost, estimated=False)
            return cost
        finally:
            with self._lock:
                self._inflight.pop(rid, None)

    def _insert(self, agent, model, tin, tout, cost, *, estimated: bool) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO experiment_usage(recorded_at_utc,run_label,agent,model,input_tokens,"
                "output_tokens,cost_usd,estimated) VALUES (?,?,?,?,?,?,?,?)",
                (self._now().isoformat(), self._label, agent, model, tin, tout, cost, int(estimated)))
        self._maybe_warn()

    def _maybe_warn(self) -> None:
        spent = self.spent()
        if spent < self.warn_at:
            return
        with self._lock, self._db:
            first = self._db.execute(
                "INSERT OR IGNORE INTO experiment_warnings(threshold_usd,sent_at_utc,spent_usd) "
                "VALUES (?,?,?)", (self.warn_at, self._now().isoformat(), spent)).rowcount == 1
        if first:
            self.warnings.append(spent)
            self._on_warning(spent, self.warn_at, self.cap)
