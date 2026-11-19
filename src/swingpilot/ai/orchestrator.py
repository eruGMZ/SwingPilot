"""AI Orchestrator determinista (REQ-G-050, REQ-G-051; data_flow.md Fases 3-5).

Responsabilidades implementadas en IMPL-1:
- Recibe ANALYSIS_REQUESTED y los resultados de la Fase 2 (REGIME_CLASSIFIED,
  ML_INFERENCE_COMPLETED, STRATEGY_CANDIDATE | NO_SETUP).
- Sin exactamente un STRATEGY_CANDIDATE: no invoca ningún agente (CR-004/CR-011).
- `precheck` opcional antes de la Fase 3 (control de costo REQ-G-096 (3), FEAT-006).
- Fase 3: Market, Macro y Strategy Analyst en paralelo, con contexto mínimo por agente y el
  mismo correlation_id. Fallo persistente de cualquiera → ciclo sin propuesta (Fail-Closed).
- Fase 4: Decision Synthesis con las salidas de Fase 2 y 3 (nunca la del Risk Analyst).
- Fase 5 (tras RISK_APPROVED): Risk Analyst consultivo → RISK_ANALYSIS_COMPLETED.
- Fija los campos deterministas de cada salida, valida contra el contrato y registra
  cada evento en el EventStore. Nunca produce órdenes ni autorizaciones.

No implementa: normalización TRADE_PROPOSAL → contrato del Risk Manager (§4.1; IMPL-3/4).
"""
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from swingpilot.audit import EventStore
from swingpilot.contracts import derive_message, validate_message
from swingpilot.contracts.agents import (
    AGENT_CONTRACT_VERSION, AgentContractError, body_schema, validate_agent_input,
    validate_agent_output,
)

from .prompts import PROMPTS
from .provider import CYCLE_DEADLINE_SECONDS, AIProviderAdapter

ORCHESTRATOR = "ai_orchestrator"
PHASE3_AGENTS = ("market_analyst", "macro_analyst", "strategy_analyst")
EVENT_FOR_AGENT = {
    "market_analyst": "MARKET_ANALYSIS_COMPLETED",
    "macro_analyst": "MACRO_ANALYSIS_COMPLETED",
    "strategy_analyst": "STRATEGY_ANALYSIS_COMPLETED",  # CR-015
    "decision_synthesis": "DECISION_SYNTHESIS_COMPLETED",
    "risk_analyst": "RISK_ANALYSIS_COMPLETED",
}
ALLOWED_EMITS = frozenset(EVENT_FOR_AGENT.values())
# Campos de `context` por agente según api_contracts.md §3.1 y §3.4; el resto se descarta
# (contexto mínimo, REQ-G-051, TC-AC-01).
CONTEXT_FIELDS = {
    "market_analyst": ("asset", "timeframes", "ohlcv", "indicators", "data_source"),
    "macro_analyst": ("news_sources", "macro_data", "time_window"),
}
_ENVELOPE_KEYS = ("analysis_id", "correlation_id", "causation_id", "schema_version", "agent",
                  "model_id", "prompt_version", "data_timestamp_utc", "analysis_timestamp_utc")
# Destino según api_contracts.md §2 (consumidor principal).
DESTINATION = {"RISK_ANALYSIS_COMPLETED": "telegram_bot"}


@dataclass
class CycleResult:
    correlation_id: str
    outcome: str  # NOT_RUN | BLOCKED | FAILED | COMPLETED
    reason: str | None = None
    outputs: dict[str, dict] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)

    @property
    def decision(self) -> str | None:
        s = self.outputs.get("decision_synthesis")
        return s.get("decision") if s and s["status"] != "ERROR" else None


def _propagate_limitations(synth: dict, outs: dict) -> dict:
    """REQ-G-056 («identifica datos faltantes»; «no oculta incertidumbre»), TC-AC-06:
    los datos faltantes declarados por la Fase 3 se añaden de forma determinista al
    `missing_data` de la síntesis (con el agente de origen), sin depender del prompt. Un
    análisis de la Fase 3 en INSUFFICIENT_DATA sin datos faltantes declarados queda
    registrado igualmente. No se inventa nada: solo se copia lo que la Fase 3 declaró."""
    declared = []
    for a in PHASE3_AGENTS:
        items = [f"{a}: {m}" for m in outs[a].get("missing_data", [])]
        if outs[a]["status"] == "INSUFFICIENT_DATA" and not items:
            items = [f"{a}: INSUFFICIENT_DATA"]
        declared += items
    merged = list(dict.fromkeys([*synth["missing_data"], *declared]))
    return {**synth, "missing_data": merged}


def _pick(ctx, fields) -> dict:
    return {k: ctx[k] for k in fields if k in ctx} if isinstance(ctx, dict) else {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class AIOrchestrator:
    def __init__(self, adapter: AIProviderAdapter, store: EventStore | None = None, *,
                 precheck: Callable[[], str | None] | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 redact: Callable[[str], str] | None = None):
        """`redact` (p. ej. CredentialVault.redact) se aplica a los mensajes de error antes
        de registrarlos: pueden contener fragmentos de texto externo o del modelo."""
        self._redact = redact or (lambda s: s)
        self._adapter, self._store = adapter, store
        self._precheck, self._clock = precheck, clock

    # ---------- utilidades ----------
    def _emit(self, res: CycleResult, msg: dict) -> dict:
        # REQ-G-058/059: la capa de IA solo publica análisis; nunca órdenes, propuestas al
        # Risk Manager, decisiones de riesgo ni autorizaciones.
        if msg["message_type"] not in ALLOWED_EMITS:
            raise PermissionError(f"el AI Orchestrator no puede emitir {msg['message_type']}")
        validate_message(msg)
        if self._store is not None:
            self._store.append(msg)
        res.events.append(msg)
        return msg

    def _run_agent(self, agent: str, cause: dict, data_ts: str, context: dict,
                   deadline: float) -> dict:
        """Nunca lanza por fallos del agente: cualquier excepción se convierte en una salida
        ERROR registrable (Fail-Closed, REQ-G-034)."""
        try:
            return self._run_agent_unsafe(agent, cause, data_ts, context, deadline)
        except Exception as e:  # noqa: BLE001 — se registra como fallo del agente
            code = "INPUT_OUT_OF_CONTRACT" if isinstance(e, AgentContractError) else "INTERNAL_ERROR"
            return self._error_output(agent, cause, data_ts, None,
                                      {"code": code, "message": f"{type(e).__name__}: {e}"})

    def _envelope(self, agent: str, cause: dict, data_ts: str, model_id: str | None) -> dict:
        return {"analysis_id": str(uuid.uuid4()), "correlation_id": cause["correlation_id"],
                "causation_id": cause["message_id"], "schema_version": AGENT_CONTRACT_VERSION,
                "agent": agent, "model_id": model_id, "prompt_version": PROMPTS[agent].version,
                "data_timestamp_utc": data_ts, "analysis_timestamp_utc": _now()}

    def _error_output(self, agent: str, cause: dict, data_ts: str, model_id: str | None,
                      error: dict, envelope: dict | None = None) -> dict:
        out = {**(envelope or self._envelope(agent, cause, data_ts, model_id)),
               "sources": [], "missing_data": [], "status": "ERROR",
               "error": {"code": error.get("code") or "UNKNOWN",
                         "message": self._redact(error.get("message") or "")}}
        validate_agent_output(agent, out)
        return out

    def _run_agent_unsafe(self, agent: str, cause: dict, data_ts: str, context: dict,
                          deadline: float) -> dict:
        prompt = PROMPTS[agent]
        agent_input = {"correlation_id": cause["correlation_id"], "causation_id": cause["message_id"],
                       "schema_version": AGENT_CONTRACT_VERSION, "agent": agent,
                       "data_timestamp_utc": data_ts, "context": context}
        validate_agent_input(agent_input)
        call = self._adapter.call_agent(
            agent, system=prompt.text, user_content=json.dumps(agent_input, ensure_ascii=False),
            output_schema=body_schema(agent), deadline=deadline)
        envelope = self._envelope(agent, cause, data_ts, call.model_id)
        if call.ok:
            out = {**call.output, **envelope}  # el sobre determinista prevalece
            try:
                validate_agent_output(agent, out)
                return out
            except AgentContractError as e:
                call.error = {"code": "OUT_OF_CONTRACT", "message": str(e)}
        return self._error_output(agent, cause, data_ts, call.model_id, call.error or {}, envelope)

    def _emit_agent(self, res: CycleResult, agent: str, out: dict, cause: dict) -> dict:
        etype = EVENT_FOR_AGENT[agent]
        return self._emit(res, derive_message(
            cause, source=agent, destination=DESTINATION.get(etype, ORCHESTRATOR),
            message_type=etype, data_timestamp_utc=cause["data_timestamp_utc"],
            timeframe=cause["timeframe"], payload=out,
            status="FAILED" if out["status"] == "ERROR" else "COMPLETED"))

    # ---------- Fases 3 y 4 ----------
    def run_cycle(self, request: dict, phase2: list[dict]) -> CycleResult:
        """`request`: ANALYSIS_REQUESTED con payload {market_context, macro_context}.
        `phase2`: mensajes de la Fase 2 del mismo correlation_id."""
        validate_message(request)
        if request["message_type"] != "ANALYSIS_REQUESTED":
            raise ValueError("run_cycle requiere ANALYSIS_REQUESTED")
        cid = request["correlation_id"]
        res = CycleResult(correlation_id=cid, outcome="NOT_RUN")
        for m in phase2:
            validate_message(m)
            if m["correlation_id"] != cid:
                raise ValueError("mensaje de Fase 2 con otro correlation_id")
        by_type: dict[str, list[dict]] = {}
        for m in phase2:
            by_type.setdefault(m["message_type"], []).append(m)

        candidates = by_type.get("STRATEGY_CANDIDATE", [])
        if "NO_SETUP" in by_type or len(candidates) != 1:
            res.reason = "NO_SETUP" if "NO_SETUP" in by_type or not candidates else "MULTIPLE_CANDIDATES"
            return res  # cero llamadas a LLM
        if self._precheck and (block := self._precheck()):
            res.outcome, res.reason = "BLOCKED", block
            return res

        deadline = self._clock() + CYCLE_DEADLINE_SECONDS
        candidate = candidates[0]
        data_ts = request["data_timestamp_utc"]
        payload = request["payload"]
        contexts = {
            "market_analyst": _pick(payload.get("market_context"), CONTEXT_FIELDS["market_analyst"]),
            "macro_analyst": _pick(payload.get("macro_context"), CONTEXT_FIELDS["macro_analyst"]),
            "strategy_analyst": {"strategy_candidates": [candidate["payload"]]},
        }
        with ThreadPoolExecutor(max_workers=len(PHASE3_AGENTS)) as pool:
            futures = {a: pool.submit(self._run_agent, a, candidate, data_ts, contexts[a], deadline)
                       for a in PHASE3_AGENTS}
            outs = {a: f.result() for a, f in futures.items()}
        res.outputs.update(outs)
        emitted = {a: self._emit_agent(res, a, outs[a], candidate) for a in PHASE3_AGENTS}

        failed = [a for a in PHASE3_AGENTS if outs[a]["status"] == "ERROR"]
        if failed:
            res.outcome, res.reason = "FAILED", "AGENT_FAILURE:" + ",".join(failed)
            return res

        # Fase 4: causa principal = MARKET_ANALYSIS_COMPLETED; el resto por analysis_id.
        primary = emitted["market_analyst"]
        phase2_ctx = {t.lower(): [m["payload"] for m in by_type.get(t, [])]
                      for t in ("REGIME_CLASSIFIED", "ML_INFERENCE_COMPLETED", "STRATEGY_CANDIDATE")}
        synth_ctx = {"phase2": phase2_ctx,
                     "inputs": {a: outs[a] for a in PHASE3_AGENTS}}
        synth = self._run_agent("decision_synthesis", primary, data_ts, synth_ctx, deadline)
        given = {outs[a]["analysis_id"] for a in PHASE3_AGENTS}
        if synth["status"] != "ERROR":
            propagated = _propagate_limitations(synth, outs)
            try:  # la salida ampliada se vuelve a validar contra el contrato
                validate_agent_output("decision_synthesis", propagated)
                synth = propagated
            except AgentContractError as e:
                synth = self._error_output(
                    "decision_synthesis", primary, data_ts, synth["model_id"],
                    {"code": "OUT_OF_CONTRACT", "message": f"tras propagar limitaciones: {e}"},
                    {k: synth[k] for k in _ENVELOPE_KEYS})
        # REQ-G-056/073: integra los tres análisis de la Fase 3 → los cita todos y solo esos.
        if synth["status"] != "ERROR" and set(synth["input_analysis_ids"]) != given:
            synth = self._error_output(
                "decision_synthesis", primary, data_ts, synth["model_id"],
                {"code": "OUT_OF_CONTRACT",
                 "message": "input_analysis_ids debe citar exactamente los 3 análisis de la Fase 3"},
                {k: synth[k] for k in _ENVELOPE_KEYS})
        res.outputs["decision_synthesis"] = synth
        self._emit_agent(res, "decision_synthesis", synth, primary)
        if synth["status"] == "ERROR":
            res.outcome, res.reason = "FAILED", "AGENT_FAILURE:decision_synthesis"
        else:
            res.outcome = "COMPLETED"
        return res

    # ---------- Fase 5 (consultiva) ----------
    def run_risk_analysis(self, risk_approved: dict, proposal: dict, system_state: dict) -> CycleResult:
        """Solo tras RISK_APPROVED. Su salida no modifica la decisión del Risk Manager."""
        validate_message(risk_approved)
        if risk_approved["message_type"] != "RISK_APPROVED":
            raise ValueError("el Risk Analyst solo corre tras RISK_APPROVED")
        res = CycleResult(correlation_id=risk_approved["correlation_id"], outcome="NOT_RUN")
        out = self._run_agent("risk_analyst", risk_approved, risk_approved["data_timestamp_utc"],
                              {"proposal": proposal, "system_state": system_state},
                              self._clock() + CYCLE_DEADLINE_SECONDS)
        res.outputs["risk_analyst"] = out
        self._emit_agent(res, "risk_analyst", out, risk_approved)
        res.outcome = "FAILED" if out["status"] == "ERROR" else "COMPLETED"
        if out["status"] == "ERROR":
            res.reason = "AGENT_FAILURE:risk_analyst"
        return res
