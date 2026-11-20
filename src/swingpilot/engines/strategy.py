"""Strategy Engine (FEAT-020; api_contracts.md §3.8 B.4–B.7.1; REQ-G-071, REQ-G-072, REQ-G-096;
DEC-011; DEC-017 Q43; DEC-018).

Determinista y sin LLM (REQ-G-057). Contiene solo el motor: NO contiene estrategias. El piloto
Trend Following H4 no se define aquí ni en ningún módulo hasta que se preregistre (DEC-018
decisión 4); sin estrategias APPROVED el resultado en Paper/Live es `NO_SETUP`
(`NO_APPROVED_STRATEGY`).

Orden de resolución de un ciclo (causa principal: E2 REGIME_CLASSIFIED):
1. Error técnico aguas arriba (E2/E3 en ERROR) o falta de la última vela de la temporalidad de
   señal → STRATEGY_CANDIDATE con `result_status = ERROR` (B.7.1). Nunca NO_SETUP.
2. Gestión de la posición abierta (no afectada por bloqueos, REQ-G-096 (3)): señal de salida
   → STRATEGY_EXIT_SIGNAL; trailing → STOP_ADJUSTMENT_REQUESTED (solo si sube el stop, B.6).
3. Señal de salida en el ciclo → NO_SETUP `EXIT_SIGNAL_PRIORITY` (DEC-011).
4. Bloqueo previo a la Fase 3 → NO_SETUP `PRE_PHASE3_BLOCK` con el estado.
5. E2/E3 en INSUFFICIENT_DATA → NO_SETUP `UPSTREAM_INSUFFICIENT_DATA`.
6. Elegibilidad: Paper/Live solo APPROVED; Research admite RESEARCH. Ninguna → `NO_APPROVED_STRATEGY`.
   ML-Based sin `INFERENCE_AVAILABLE` y estrategias cuyo régimen requerido no se cumple → NOT_ELIGIBLE.
7. Candidatos: 0 → `NO_CANDIDATE`; ≥ 2 (aunque coincidan) → `MULTIPLE_ENTRY_CANDIDATES`; 1 →
   STRATEGY_CANDIDATE. Excepción de una estrategia → ERROR `INTERNAL_ERROR`; candidato mal
   formado → ERROR `INVALID_CANDIDATE`. Regla binaria, sin confianza (CR-011).
"""
import uuid
from dataclasses import dataclass, field
from typing import Protocol

from swingpilot.market_data.candles import ms_to_iso

from .common import MarketInput, base_payload, engine_message
from .schemas import PRE_PHASE3_DETAILS, EnginePayloadError, validate_engine_payload

ENGINE = "strategy_engine"
ENGINE_VERSION = "0.1.0"
MODES = ("RESEARCH", "PAPER", "LIVE")


@dataclass(frozen=True)
class EntryProposal:
    conditions: list[dict]
    entry_zone: dict
    entry_reference_price: float
    stop_loss: dict
    exit_mechanism: dict
    invalidation_conditions: list[str]
    take_profit: float | None = None


@dataclass(frozen=True)
class EntryEvaluation:
    proposal: EntryProposal | None
    failed_conditions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExitProposal:
    exit_reason: str              # EXIT_CONDITION | INVALIDATION | TIME_EXIT
    conditions: list[dict]
    reference_price: float


@dataclass(frozen=True)
class StopProposal:
    requested_stop: float
    method: str
    parameters: dict


@dataclass(frozen=True)
class OpenPosition:
    operation_id: str | None
    strategy_id: str
    strategy_version: str
    current_stop: float


class StrategyDefinition(Protocol):
    strategy_id: str
    version: str
    family: str                   # TREND_FOLLOWING | … | ML_BASED
    status: str                   # APPROVED | RESEARCH
    experiment_ref: str | None
    signal_timeframe: str
    required_regimes: tuple[str, ...] | None

    def evaluate_entry(self, market: MarketInput, regime: dict, ml: dict) -> EntryEvaluation: ...
    def evaluate_exit(self, market: MarketInput, position: OpenPosition) -> ExitProposal | None: ...
    def trailing_stop(self, market: MarketInput, position: OpenPosition) -> StopProposal | None: ...


class StrategyEngine:
    def __init__(self, strategies: list[StrategyDefinition] | None = None, *, signal_timeframe: str = "H4"):
        self.strategies = list(strategies or [])
        keys = [(s.strategy_id, s.version) for s in self.strategies]
        if len(keys) != len(set(keys)):
            raise ValueError("estrategia duplicada (id+versión)")
        for s in self.strategies:
            if s.status not in ("APPROVED", "RESEARCH"):
                raise ValueError(f"{s.strategy_id}: estado no válido {s.status}")
            if s.status == "APPROVED" and not s.experiment_ref:
                raise ValueError(f"{s.strategy_id}: APPROVED exige experiment_ref (REQ-G-072)")
        self.signal_timeframe = signal_timeframe

    # ------------------------------------------------------------------ utilidades
    def _refs(self, market: MarketInput) -> dict:
        return {self.signal_timeframe: market.data_ref(self.signal_timeframe)}

    def _msg(self, cause, market, mtype, payload, destination="ai_orchestrator"):
        tf = self.signal_timeframe
        return engine_message(cause, source=ENGINE, message_type=mtype, payload=payload,
                              data_timestamp_utc=market.data_timestamp(tf), timeframe=tf, destination=destination)

    def _error(self, cause, market, regime, ml, code, message, stage, upstream=None, strategy=None):
        p = {**base_payload(ENGINE, ENGINE_VERSION, None, "ERROR", self._refs(market), error={
                 "code": code, "message": message, "stage": stage, "upstream_message_id": upstream,
                 "strategy_id": strategy.strategy_id if strategy else None,
                 "strategy_version": strategy.version if strategy else None}),
             "regime_message_id": regime["message_id"] if regime else None,
             "ml_inference_message_id": ml["message_id"] if ml else None}
        return self._msg(cause, market, "STRATEGY_CANDIDATE", p)

    def _no_setup(self, cause, market, reason, detail=None, evaluated=(), discarded=(), exit_ref=None,
                  status="COMPLETED", missing=None):
        p = {**base_payload(ENGINE, ENGINE_VERSION, None, status, self._refs(market), missing),
             "reason_code": reason, "reason_detail": detail, "evaluated_strategies": list(evaluated),
             "discarded_candidates": list(discarded), "exit_signal_ref": exit_ref, "llm_calls": 0}
        return self._msg(cause, market, "NO_SETUP", p)

    def _signal_close(self, market) -> str:
        return market.data_timestamp(self.signal_timeframe)

    # ------------------------------------------------------------------ ciclo
    def run(self, regime_msg: dict, ml_msg: dict, market: MarketInput, *, mode: str,
            block: str | None = None, position: OpenPosition | None = None) -> list[dict]:
        """Devuelve los eventos del ciclo en orden: [STRATEGY_EXIT_SIGNAL?, STOP_ADJUSTMENT_REQUESTED?,
        STRATEGY_CANDIDATE | NO_SETUP]. Causa principal de todos: E2 (regime_msg)."""
        if mode not in MODES:
            raise ValueError(f"modo no válido: {mode}")
        if block is not None and block not in PRE_PHASE3_DETAILS:
            raise ValueError(f"bloqueo no válido: {block}")
        cause = regime_msg
        rp, mp = regime_msg["payload"], ml_msg["payload"]
        if ml_msg["correlation_id"] != regime_msg["correlation_id"]:
            raise ValueError("E2 y E3 de ciclos distintos")
        # 1. errores técnicos aguas arriba / datos
        for up, stage in ((regime_msg, "REGIME_INPUT"), (ml_msg, "ML_INPUT")):
            if up["payload"]["result_status"] == "ERROR" or up["status"] == "FAILED":
                return [self._error(cause, market, regime_msg, ml_msg, "UPSTREAM_ERROR",
                                    f"{up['message_type']} en ERROR", stage, upstream=up["message_id"])]
        if not market.has_last_closed(self.signal_timeframe):
            return [self._error(cause, market, regime_msg, ml_msg, "DATA_UNAVAILABLE",
                                f"falta la última vela {self.signal_timeframe} cerrada (REQ-G-070)", "INPUT_VALIDATION")]
        out: list[dict] = []
        exit_msg = None
        # 2. gestión de la posición abierta
        if position is not None:
            strat = next((s for s in self.strategies if (s.strategy_id, s.version) ==
                          (position.strategy_id, position.strategy_version)), None)
            if strat is None:
                return [self._error(cause, market, regime_msg, ml_msg, "SPEC_NOT_FOUND",
                                    "estrategia de la posición abierta no cargada", "STRATEGY_EVALUATION")]
            try:
                ex = strat.evaluate_exit(market, position)
                st = None if ex else strat.trailing_stop(market, position)
            except Exception as exc:   # noqa: BLE001
                return [self._error(cause, market, regime_msg, ml_msg, "INTERNAL_ERROR",
                                    f"{type(exc).__name__}: {exc}", "STRATEGY_EVALUATION", strategy=strat)]
            if ex is not None:
                p = {**base_payload(ENGINE, ENGINE_VERSION, None, "COMPLETED", self._refs(market)),
                     "exit_id": str(uuid.uuid4()), "operation_id": position.operation_id,
                     "strategy_id": strat.strategy_id, "strategy_version": strat.version,
                     "exit_reason": ex.exit_reason, "conditions": ex.conditions,
                     "signal_timeframe": self.signal_timeframe, "signal_bar_close_utc": self._signal_close(market),
                     "reference_price": ex.reference_price, "supersedes_entry_candidates": []}
                exit_msg = self._msg(cause, market, "STRATEGY_EXIT_SIGNAL", p, destination="execution_engine")
                out.append(exit_msg)
            elif st is not None and st.requested_stop > position.current_stop:
                p = {**base_payload(ENGINE, ENGINE_VERSION, None, "COMPLETED", self._refs(market)),
                     "request_id": str(uuid.uuid4()), "operation_id": position.operation_id,
                     "strategy_id": strat.strategy_id, "strategy_version": strat.version,
                     "current_stop": position.current_stop, "requested_stop": st.requested_stop,
                     "method": st.method, "parameters": st.parameters,
                     "signal_timeframe": self.signal_timeframe, "signal_bar_close_utc": self._signal_close(market)}
                out.append(self._msg(cause, market, "STOP_ADJUSTMENT_REQUESTED", p, destination="risk_manager"))
        # 3–5. prioridad de salida, bloqueos, insuficiencia
        if exit_msg is not None:
            return out + [self._no_setup(cause, market, "EXIT_SIGNAL_PRIORITY", exit_ref=exit_msg["message_id"])]
        if block is None and position is not None:
            block = "OPEN_POSITION"   # INV-003
        if block is not None:
            return out + [self._no_setup(cause, market, "PRE_PHASE3_BLOCK", detail=block)]
        insufficient = [f"{m['message_type']}: {x}" for m in (regime_msg, ml_msg)
                        if m["payload"]["result_status"] == "INSUFFICIENT_DATA" for x in m["payload"]["missing_data"]]
        if insufficient:
            return out + [self._no_setup(cause, market, "UPSTREAM_INSUFFICIENT_DATA", status="INSUFFICIENT_DATA",
                                         missing=insufficient)]
        # 6. elegibilidad
        allowed = ("APPROVED",) if mode in ("PAPER", "LIVE") else ("APPROVED", "RESEARCH")
        eligible = [s for s in self.strategies if s.status in allowed]
        if not eligible:
            return out + [self._no_setup(cause, market, "NO_APPROVED_STRATEGY", detail=f"modo {mode}")]
        evaluated, proposals = [], []
        for s in eligible:
            if s.family == "ML_BASED" and mp["inference_status"] != "INFERENCE_AVAILABLE":
                evaluated.append(_ev(s, "NOT_ELIGIBLE", ["ml_engine: " + mp["inference_status"]]))
                continue
            if s.required_regimes is not None and rp["regime_label"] not in s.required_regimes:
                evaluated.append(_ev(s, "NOT_ELIGIBLE", [f"régimen {rp['regime_label']} fuera de {list(s.required_regimes)}"]))
                continue
            try:
                res = s.evaluate_entry(market, rp, mp)
            except Exception as exc:   # noqa: BLE001
                return out + [self._error(cause, market, regime_msg, ml_msg, "INTERNAL_ERROR",
                                          f"{type(exc).__name__}: {exc}", "STRATEGY_EVALUATION", strategy=s)]
            if res.proposal is None:
                evaluated.append(_ev(s, "NO_SIGNAL", res.failed_conditions))
            else:
                payload = self._candidate_payload(s, res.proposal, regime_msg, ml_msg, market, mode)
                try:
                    validate_engine_payload("STRATEGY_CANDIDATE", payload)
                except EnginePayloadError as exc:
                    return out + [self._error(cause, market, regime_msg, ml_msg, "INVALID_CANDIDATE", str(exc),
                                              "CANDIDATE_VALIDATION", strategy=s)]
                evaluated.append(_ev(s, "CANDIDATE", []))
                proposals.append((s, payload))
        # 7. resolución binaria
        if not proposals:
            return out + [self._no_setup(cause, market, "NO_CANDIDATE", evaluated=evaluated)]
        if len(proposals) > 1:
            discarded = [{"candidate_id": p["candidate_id"], "strategy_id": s.strategy_id,
                          "strategy_version": s.version, "discard_reason": "CONFLICT_MULTIPLE_ENTRIES"}
                         for s, p in proposals]
            evaluated = [{**e, "result": "DISCARDED"} if e["result"] == "CANDIDATE" else e for e in evaluated]
            return out + [self._no_setup(cause, market, "MULTIPLE_ENTRY_CANDIDATES", evaluated=evaluated,
                                         discarded=discarded)]
        return out + [self._msg(cause, market, "STRATEGY_CANDIDATE", proposals[0][1])]

    def _candidate_payload(self, s, prop: EntryProposal, regime_msg, ml_msg, market, mode) -> dict:
        return {**base_payload(ENGINE, ENGINE_VERSION, s.version, "COMPLETED", self._refs(market)),
                "candidate_id": str(uuid.uuid4()), "candidate_type": "ENTRY_LONG",
                "strategy_id": s.strategy_id, "strategy_version": s.version, "strategy_family": s.family,
                "strategy_status": s.status, "operating_mode": mode, "experiment_ref": s.experiment_ref,
                "regime_message_id": regime_msg["message_id"], "ml_inference_message_id": ml_msg["message_id"],
                "signal_timeframe": self.signal_timeframe, "signal_bar_close_utc": self._signal_close(market),
                "conditions": prop.conditions, "entry_zone": prop.entry_zone,
                "entry_reference_price": prop.entry_reference_price, "stop_loss": prop.stop_loss,
                "take_profit": prop.take_profit, "exit_mechanism": prop.exit_mechanism,
                "invalidation_conditions": prop.invalidation_conditions}


def _ev(s, result, failed):
    return {"strategy_id": s.strategy_id, "strategy_version": s.version, "result": result,
            "failed_conditions": list(failed)}
