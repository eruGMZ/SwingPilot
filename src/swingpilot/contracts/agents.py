"""Contratos de entrada/salida de los agentes LLM (api_contracts.md §3; REQ-G-060, REQ-G-064).

Diseño de implementación: el LLM produce solo el «cuerpo» (campos específicos del agente
+ sources, missing_data, status). Los campos deterministas de §3.0 (analysis_id,
correlation_id, causation_id, schema_version, agent, model_id, prompt_version,
data_timestamp_utc, analysis_timestamp_utc) los fija el AI Orchestrator, no el LLM.
La salida completa (cuerpo + campos comunes) se valida con OUTPUT_SCHEMAS.
"""
import copy
from typing import Any

from jsonschema import Draft202012Validator

from .versioning import check_compatibility

AGENT_CONTRACT_VERSION = "1.0.0"
AGENTS = ("market_analyst", "macro_analyst", "strategy_analyst", "decision_synthesis", "risk_analyst")

_STR = {"type": "string"}
_STRS = {"type": "array", "items": _STR}
_NUMS = {"type": "array", "items": {"type": "number"}}
_CONF = {"enum": ["HIGH", "MEDIUM", "LOW"]}
_STMT = {"enum": ["FACT", "INFERENCE", "RECOMMENDATION"]}
_TREND = {"enum": ["BULLISH", "BEARISH", "NEUTRAL", "UNCLEAR"]}
_UUID = {"type": "string", "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"}
_SEMVER = {"type": "string", "pattern": r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"}
_TS = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"}


def _obj(props: dict) -> dict:
    return {"type": "object", "additionalProperties": False,
            "required": list(props), "properties": props}


def _nullable(s: dict) -> dict:
    return {"anyOf": [s, {"type": "null"}]}


# Campos que el LLM sí produce en todos los agentes (§3.0).
_BODY_COMMON = {
    "sources": _STRS,
    "missing_data": _STRS,
    "status": {"enum": ["COMPLETED", "INSUFFICIENT_DATA"]},
}

_SPECIFIC = {
    # §3.2
    "market_analyst": {
        "observations": {"type": "array", "items": _obj({
            "timeframe": {"enum": ["D1", "H4", "H1"]}, "observation": _STR, "evidence": _STR,
            "confidence": _CONF, "statement_type": _STMT})},
        "key_levels": _obj({"support": _NUMS, "resistance": _NUMS}),
        "trend_assessment": _obj({"D1": _TREND, "H4": _TREND}),
        "limitations": _STRS,
    },
    # §3.5
    "macro_analyst": {
        "events": {"type": "array", "items": _obj({
            "description": _STR, "potential_impact": _STR, "time_horizon": _STR, "source": _STR,
            "publication_date": _STR, "confirmation": {"enum": ["CONFIRMED", "RUMOR", "SPECULATION"]},
            "uncertainty": _CONF, "statement_type": _STMT})},
    },
    # §3.6
    "strategy_analyst": {
        "evaluations": {"type": "array", "items": _obj({
            "strategy_id": _STR, "strategy_version": _STR, "logic_assessment": _STR,
            "activation_conditions_assessment": _STR, "signal_invalidation_coherence": _STR,
            "weakening_conditions": _STRS, "comparison": _nullable(_STR), "discard_reasons": _STRS,
            "statement_type": _STMT})},
    },
    # §3.3
    "decision_synthesis": {
        "decision": {"enum": ["TRADE_PROPOSAL", "INSUFFICIENT_INFO", "DISCARD", "DISAGREEMENT"]},
        "trade_proposal": _nullable(_obj({
            "asset": {"enum": ["BTC/USDT"]}, "direction": {"enum": ["LONG"]},
            "entry_zone": _obj({"min": {"type": "number"}, "max": {"type": "number"}}),
            "stop_loss": {"type": "number"}, "take_profit": _nullable({"type": "number"}),
            "strategy_id": _STR, "strategy_version": _STR, "rationale": _STR,
            "conflicting_signals": _STRS, "uncertainty_notes": _STR})),
        "agent_summaries": _obj({a: _obj({"key_finding": _STR, "confidence": _CONF})
                                 for a in ("market_analyst", "macro_analyst", "strategy_analyst")}),
        "input_analysis_ids": _STRS,
    },
    # §3.7
    "risk_analyst": {
        "hidden_risks": _STRS, "entry_stop_target_inconsistencies": _STRS,
        "external_event_exposure": _STRS, "operational_data_risks": _STRS,
        "challenged_assumptions": _STRS, "advisory_only": {"enum": [True]},
    },
}

# Esquema que se envía al modelo (output_config.format).
BODY_SCHEMAS: dict[str, dict] = {a: _obj({**_SPECIFIC[a], **_BODY_COMMON}) for a in AGENTS}

_ENVELOPE = {
    "analysis_id": _UUID, "correlation_id": _UUID, "causation_id": _UUID,
    "schema_version": _SEMVER, "model_id": _nullable(_STR), "prompt_version": _SEMVER,
    "data_timestamp_utc": _TS, "analysis_timestamp_utc": _TS,
}


def _output_schema(agent: str) -> dict:
    """Salida completa. status ERROR: cuerpo específico ausente y `error` obligatorio."""
    ok = _obj({**_SPECIFIC[agent], **_BODY_COMMON, **_ENVELOPE, "agent": {"enum": [agent]}})
    ok["properties"]["model_id"] = _STR  # una salida válida siempre tiene modelo efectivo
    err = _obj({**_ENVELOPE, "agent": {"enum": [agent]}, "sources": _STRS, "missing_data": _STRS,
                "status": {"enum": ["ERROR"]},
                "error": _obj({"code": _STR, "message": _STR})})
    return {"oneOf": [ok, err]}


OUTPUT_SCHEMAS: dict[str, dict] = {a: _output_schema(a) for a in AGENTS}

INPUT_SCHEMA: dict[str, Any] = _obj({
    "correlation_id": _UUID, "causation_id": _UUID, "schema_version": _SEMVER,
    "agent": {"enum": list(AGENTS)}, "data_timestamp_utc": _TS, "context": {"type": "object"},
})

for _s in (*BODY_SCHEMAS.values(), *OUTPUT_SCHEMAS.values(), INPUT_SCHEMA):
    Draft202012Validator.check_schema(_s)


class AgentContractError(ValueError):
    pass


def _validate(schema: dict, doc: Any, what: str) -> None:
    errs = sorted(Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
    if errs:
        raise AgentContractError(f"{what}: " + "; ".join(
            f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs))


def validate_agent_input(doc: dict) -> None:
    _validate(INPUT_SCHEMA, doc, "entrada de agente")
    check_compatibility(doc["schema_version"], AGENT_CONTRACT_VERSION)


def validate_agent_output(agent: str, doc: dict) -> None:
    """Valida la salida completa y su versión (TC-AC-02). Reglas semánticas de §3.3:
    TRADE_PROPOSAL exige trade_proposal; cualquier otra decisión lo exige nulo."""
    if agent not in OUTPUT_SCHEMAS:
        raise AgentContractError(f"agente desconocido: {agent!r}")
    _validate(OUTPUT_SCHEMAS[agent], doc, f"salida de {agent}")
    check_compatibility(doc["schema_version"], AGENT_CONTRACT_VERSION)
    if agent == "decision_synthesis" and doc["status"] != "ERROR":
        if (doc["decision"] == "TRADE_PROPOSAL") != (doc["trade_proposal"] is not None):
            raise AgentContractError("decision y trade_proposal inconsistentes")


def body_schema(agent: str) -> dict:
    return copy.deepcopy(BODY_SCHEMAS[agent])
