"""Normalización de TRADE_PROPOSAL (FEAT-021; api_contracts.md §3.8 B.8, §3.3, §4.1 v1.1.0; REQ-G-073).

Componente determinista, separado de la capa de IA. El AI Orchestrator no puede emitir
propuestas (REQ-G-058/059): la síntesis (LLM) solo propone, y aquí se construye la
TRADE_PROPOSAL de §4.1 copiando de STRATEGY_CANDIDATE todos los campos operativos (activo,
dirección, estrategia y versión, precio de entrada, stop y mecanismo de salida). El LLM no fija
precios.

Consistencia exigida a la síntesis (B.8.2): misma estrategia y versión, stop idéntico,
`entry_zone` contenida en la del candidato y `take_profit` nulo o igual. Si falla, no se emite
TRADE_PROPOSAL y se devuelve la inconsistencia (`PROPOSAL_INCONSISTENT_WITH_CANDIDATE`).
La propuesta se valida contra §4.1 v1.1.0 antes de emitirse (`OUT_OF_CONTRACT` si no).
TRADE_PROPOSAL no es orden ni autorización; en IMPL-3 ningún consumidor de ejecución la recibe.
"""
import uuid
from dataclasses import dataclass, field

from jsonschema import Draft202012Validator

from swingpilot.contracts import derive_message

PROPOSAL_SCHEMA_VERSION = "1.1.0"
_UUID = {"type": "string", "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"}
_SEMVER = {"type": "string", "pattern": r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"}
_POS = {"type": "number", "exclusiveMinimum": 0}
_STR = {"type": "string", "minLength": 1}
_V10 = {
    "proposal_id": _UUID, "correlation_id": _UUID, "schema_version": _SEMVER,
    "timestamp_utc": {"type": "string"}, "asset": {"const": "BTC/USDT"}, "direction": {"const": "LONG"},
    "entry_price_target": _POS, "stop_loss_price": _POS, "strategy_id": _STR, "strategy_version": _SEMVER,
    "exit_mechanism": {"type": "object", "additionalProperties": False,
                       "required": ["type", "trigger_condition", "execution_method", "failure_procedure"],
                       "properties": {"type": {"enum": ["STOP_LOSS", "TRAILING_STOP", "TARGET_PRICE"]},
                                      "trigger_condition": _STR, "execution_method": _STR, "failure_procedure": _STR}},
}
_V11_ADD = {
    "source_candidate_id": _UUID, "source_candidate_message_id": _UUID, "synthesis_analysis_id": _UUID,
    "entry_zone": {"type": "object", "additionalProperties": False, "required": ["min", "max"],
                   "properties": {"min": _POS, "max": _POS}},
    "take_profit_price": {"anyOf": [_POS, {"type": "null"}]},
}
PROPOSAL_V10 = {"type": "object", "additionalProperties": False, "required": list(_V10), "properties": _V10}
PROPOSAL_V11 = {"type": "object", "additionalProperties": False, "required": list(_V10) + list(_V11_ADD),
                "properties": {**_V10, **_V11_ADD}}
_VAL = {"1.0.0": Draft202012Validator(PROPOSAL_V10), "1.1.0": Draft202012Validator(PROPOSAL_V11)}
INCONSISTENT = "PROPOSAL_INCONSISTENT_WITH_CANDIDATE"


class ProposalContractError(ValueError):
    pass


def validate_trade_proposal(doc: dict) -> None:
    """TC-NORM-003: v1.1.0 valida; v1.0.0 sigue siendo legible (con su esquema)."""
    v = _VAL.get(doc.get("schema_version"))
    if v is None:
        raise ProposalContractError(f"versión de TRADE_PROPOSAL no soportada: {doc.get('schema_version')}")
    errs = list(v.iter_errors(doc))
    if errs:
        raise ProposalContractError("; ".join(e.message for e in errs[:5]))


@dataclass
class NormalizationResult:
    proposal_message: dict | None
    status: str                     # EMITTED | NOT_A_PROPOSAL | PROPOSAL_INCONSISTENT_WITH_CANDIDATE | OUT_OF_CONTRACT
    problems: list[str] = field(default_factory=list)


def normalize(candidate_msg: dict, synthesis_msg: dict) -> NormalizationResult:
    if candidate_msg["message_type"] != "STRATEGY_CANDIDATE" or synthesis_msg["message_type"] != "DECISION_SYNTHESIS_COMPLETED":
        raise ValueError("normalize requiere STRATEGY_CANDIDATE y DECISION_SYNTHESIS_COMPLETED")
    if candidate_msg["correlation_id"] != synthesis_msg["correlation_id"]:
        raise ValueError("candidato y síntesis de ciclos distintos")
    c, s = candidate_msg["payload"], synthesis_msg["payload"]
    if c.get("result_status") != "COMPLETED" or candidate_msg["status"] != "COMPLETED":
        return NormalizationResult(None, "NOT_A_PROPOSAL", ["candidato en ERROR"])
    if s.get("status") == "ERROR" or s.get("decision") != "TRADE_PROPOSAL" or not s.get("trade_proposal"):
        return NormalizationResult(None, "NOT_A_PROPOSAL", [f"decisión {s.get('decision')}"])
    tp = s["trade_proposal"]
    problems = []
    if (tp["strategy_id"], tp["strategy_version"]) != (c["strategy_id"], c["strategy_version"]):
        problems.append("strategy_id/strategy_version distintos del candidato")
    if tp["stop_loss"] != c["stop_loss"]["price"]:
        problems.append(f"stop_loss {tp['stop_loss']} ≠ candidato {c['stop_loss']['price']}")
    z, cz = tp["entry_zone"], c["entry_zone"]
    if not (cz["min"] <= z["min"] <= z["max"] <= cz["max"]):
        problems.append("entry_zone fuera de la del candidato")
    if tp["take_profit"] is not None and tp["take_profit"] != c["take_profit"]:
        problems.append("take_profit distinto del candidato")
    if problems:
        return NormalizationResult(None, INCONSISTENT, problems)
    proposal = {
        "proposal_id": str(uuid.uuid4()), "correlation_id": synthesis_msg["correlation_id"],
        "schema_version": PROPOSAL_SCHEMA_VERSION, "timestamp_utc": synthesis_msg["timestamp_utc"],
        "asset": "BTC/USDT", "direction": "LONG",
        "entry_price_target": c["entry_reference_price"], "stop_loss_price": c["stop_loss"]["price"],
        "strategy_id": c["strategy_id"], "strategy_version": c["strategy_version"],
        "exit_mechanism": c["exit_mechanism"],
        "source_candidate_id": c["candidate_id"], "source_candidate_message_id": candidate_msg["message_id"],
        "synthesis_analysis_id": s["analysis_id"], "entry_zone": c["entry_zone"],
        "take_profit_price": c["take_profit"],
    }
    try:
        validate_trade_proposal(proposal)
    except ProposalContractError as exc:
        return NormalizationResult(None, "OUT_OF_CONTRACT", [str(exc)])
    msg = derive_message(synthesis_msg, source="decision_synthesis", destination="risk_manager",
                         message_type="TRADE_PROPOSAL", data_timestamp_utc=synthesis_msg["data_timestamp_utc"],
                         timeframe=synthesis_msg["timeframe"], payload=proposal, status="COMPLETED")
    return NormalizationResult(msg, "EMITTED")
