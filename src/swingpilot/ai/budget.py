"""Control de costo de la IA (REQ-G-096, REQ-G-034, DEC-009, DEC-010 Q29; TC-AI-006/007).

(1) Gasto mensual ≥ $5 → no se hacen llamadas (también a mitad de ciclo).
(2) Al alcanzar $4 → AI_BUDGET_WARNING una sola vez por mes calendario.
(3) EntryGate antes de la Fase 3: posición abierta, bloqueo de entradas o modo seguro →
    cero llamadas; estado no disponible → bloqueo (Fail-Closed, INV-012).
(5) `usage` y costo de cada llamada en una tabla append-only (persiste entre reinicios).
(4) límite en la consola de Anthropic: configuración manual del propietario, fuera del código.

Zona horaria del «mes calendario»: America/Mexico_City (DEC-014 Q31).

Precios (DEC-009, USD por millón de tokens): Haiku 5.5 $0.10/$0.50; Sonnet 5.5 $2/$10.
Decisión de implementación: si la entrada de Haiku 5.5 supera 100K tokens se aplica su
tarifa alta ($0.50/$2.50) a toda la llamada (conservador).
"""
import sqlite3
import threading
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

MONTHLY_CAP_USD = 5.0
WARNING_THRESHOLD_USD = 4.0
PRICES = {  # USD / 1M tokens: (input, output)
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0),
}
BUDGET_TZ = ZoneInfo("America/Mexico_City")  # DEC-014 Q31
HAIKU_LONG_PROMPT = (100_000, (0.50, 2.50))
ENTRY_LOCKS = frozenset({"LOSS_STREAK_LOCK", "MONTHLY_DRAWDOWN_LOCK", "MONTHLY_TRADE_LIMIT_LOCK",
                         "DATA_UNAVAILABLE", "EXCHANGE_DESYNC", "MANUAL_REVIEW"})
# Estados del Risk Manager (REQ-G-025). Un estado desconocido bloquea (Fail-Closed).
KNOWN_STATES = ENTRY_LOCKS | {"ACTIVE", "POSITION_OPEN"}

_DDL = """
CREATE TABLE IF NOT EXISTS ai_usage (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL, recorded_at_utc TEXT NOT NULL, agent TEXT NOT NULL, model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL, cost_usd REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_ai_usage_month ON ai_usage(month);
CREATE TABLE IF NOT EXISTS ai_budget_warnings (month TEXT PRIMARY KEY, sent_at_utc TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS ai_usage_no_update BEFORE UPDATE ON ai_usage
BEGIN SELECT RAISE(ABORT, 'ai_usage es inmutable'); END;
CREATE TRIGGER IF NOT EXISTS ai_usage_no_delete BEFORE DELETE ON ai_usage
BEGIN SELECT RAISE(ABORT, 'ai_usage es inmutable'); END;
"""


class UnknownModelPrice(KeyError):
    pass


def call_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in PRICES:
        raise UnknownModelPrice(model)  # sin precio conocido no se puede medir: Fail-Closed
    pin, pout = PRICES[model]
    if model == "claude-haiku-5-5" and input_tokens > HAIKU_LONG_PROMPT[0]:
        pin, pout = HAIKU_LONG_PROMPT[1]
    return (input_tokens * pin + output_tokens * pout) / 1_000_000


class AIBudget:
    def __init__(self, path: str | Path, *, tz: tzinfo = BUDGET_TZ,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 on_warning: Callable[[str, float], None] | None = None):
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.executescript(_DDL)
        self._tz, self._now, self._on_warning = tz, now, on_warning
        self._lock = threading.Lock()

    def close(self) -> None:
        self._db.close()

    def _month(self) -> str:
        return self._now().astimezone(self._tz).strftime("%Y-%m")

    def spent_this_month(self) -> float:
        with self._lock:
            row = self._db.execute("SELECT COALESCE(SUM(cost_usd),0) FROM ai_usage WHERE month=?",
                                   (self._month(),)).fetchone()
        return float(row[0])

    def cap_reached(self) -> bool:
        return self.spent_this_month() >= MONTHLY_CAP_USD

    def can_call(self) -> bool:
        return not self.cap_reached()

    def record(self, agent: str, model: str | None, input_tokens: int | None,
               output_tokens: int | None) -> float:
        """Registra una llamada con respuesta. Sin modelo o tokens, o con un modelo sin
        precio conocido, lanza error: el gasto no se subestima en silencio."""
        if model is None or input_tokens is None or output_tokens is None:
            raise ValueError("usage incompleto: no se puede medir el costo")
        cost = call_cost_usd(model, input_tokens, output_tokens)
        month = self._month()
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO ai_usage(month,recorded_at_utc,agent,model,input_tokens,output_tokens,cost_usd)"
                " VALUES (?,?,?,?,?,?,?)",
                (month, self._now().astimezone(timezone.utc).isoformat(), agent, model,
                 input_tokens, output_tokens, cost))
        self._maybe_warn(month)
        return cost

    def _maybe_warn(self, month: str) -> None:
        spent = self.spent_this_month()
        if spent < WARNING_THRESHOLD_USD:
            return
        with self._lock, self._db:
            cur = self._db.execute(
                "INSERT OR IGNORE INTO ai_budget_warnings(month, sent_at_utc) VALUES (?,?)",
                (month, self._now().astimezone(timezone.utc).isoformat()))
            first = cur.rowcount == 1
        if first and self._on_warning:
            self._on_warning(month, spent)


class EntryGate:
    """Control previo a la Fase 3 (REQ-G-096 (3) y (1)). `state()` devuelve
    {"open_position": bool, "locks": iterable[str] (estados activos del Risk Manager),
    "safe_mode": bool}. Devuelve el motivo
    del bloqueo o None si se permiten llamadas a LLM."""

    def __init__(self, state: Callable[[], dict], budget: AIBudget):
        self._state, self._budget = state, budget

    def __call__(self) -> str | None:
        try:
            s = self._state()
            open_position, locks, safe_mode = s["open_position"], set(s["locks"]), s["safe_mode"]
        except Exception:
            return "STATE_UNAVAILABLE"
        if not isinstance(open_position, bool) or not isinstance(safe_mode, bool):
            return "STATE_UNAVAILABLE"
        if unknown := sorted(locks - KNOWN_STATES):
            return "UNKNOWN_STATE:" + ",".join(unknown)
        if open_position or "POSITION_OPEN" in locks:
            return "OPEN_POSITION"
        if blocking := sorted(locks & ENTRY_LOCKS):
            return "ENTRY_LOCK:" + ",".join(blocking)
        if safe_mode:
            return "SAFE_MODE"
        if self._budget.cap_reached():
            return "AI_BUDGET_CAP_REACHED"
        return None


def budget_warning_emitter(store) -> Callable[[str, float], None]:
    """Callback para AIBudget.on_warning: registra AI_BUDGET_WARNING (consumidores: Telegram
    Bot y Audit, api_contracts.md §2). El envío por Telegram es de una fase posterior."""
    from swingpilot.contracts import new_message

    def emit(month: str, spent: float) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        store.append(new_message(
            source="ai_orchestrator", destination="telegram_bot", message_type="AI_BUDGET_WARNING",
            data_timestamp_utc=ts, status="COMPLETED",
            payload={"month": month, "spent_usd": round(spent, 6),
                     "threshold_usd": WARNING_THRESHOLD_USD, "cap_usd": MONTHLY_CAP_USD}))
    return emit
