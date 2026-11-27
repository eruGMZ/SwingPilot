"""Esquemas de los payloads de la Fase 2 (api_contracts.md §3.8, CR-018, DEC-019; TC-MSG-004).

Reglas comunes (B.0): `engine`, `engine_version`, `spec_version`, `result_status`,
`data_refs`, `missing_data`, `error`. ERROR exige `error`; INSUFFICIENT_DATA exige
`missing_data` no vacío. Sin campos de confianza (CR-011).
"""
import copy
from typing import Any

from jsonschema import Draft202012Validator

ENGINE_SCHEMA_VERSION = "1.0.0"

_STR = {"type": "string", "minLength": 1}
_STRS = {"type": "array", "items": {"type": "string"}}
_UUID = {"type": "string", "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"}
_SEMVER = {"type": "string", "pattern": r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"}
_TS = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"}
_POS = {"type": "number", "exclusiveMinimum": 0}
_TF = {"enum": ["D1", "H4", "H1"]}


def _null(s):
    return {"anyOf": [s, {"type": "null"}]}


ERROR_CODES = ("DATA_UNAVAILABLE", "DATA_STALE", "DATA_INCONSISTENT", "UPSTREAM_ERROR", "SPEC_NOT_FOUND",
               "INVALID_STOP_REQUEST", "INVALID_CANDIDATE", "INTERNAL_ERROR", "ELIGIBILITY_UNDETERMINED")
ERROR_STAGES = ("INPUT_VALIDATION", "REGIME_INPUT", "ML_INPUT", "STRATEGY_EVALUATION",
                "CANDIDATE_VALIDATION", "INTERNAL")

_DATA_REF = {"type": "object", "additionalProperties": False,
             "required": ["last_closed_open_time_utc", "bars_used", "source", "snapshot_id"],
             "properties": {"last_closed_open_time_utc": _null(_TS), "bars_used": {"type": "integer", "minimum": 0},
                            "source": {"enum": ["binance_ws", "binance_rest", "snapshot"]},
                            "snapshot_id": _null(_STR)}}

_ERROR = {"type": "object", "additionalProperties": False, "required": ["code", "message"],
          "properties": {"code": {"enum": list(ERROR_CODES)}, "message": {"type": "string"},
                         "stage": {"enum": list(ERROR_STAGES)}, "upstream_message_id": _null(_UUID),
                         "strategy_id": _null(_STR), "strategy_version": _null(_SEMVER)}}

COMMON = {
    "engine": {"enum": ["regime_engine", "ml_engine", "strategy_engine"]},
    "engine_version": _SEMVER,
    "spec_version": _null(_SEMVER),
    "result_status": {"enum": ["COMPLETED", "INSUFFICIENT_DATA", "ERROR"]},
    "data_refs": {"type": "object", "propertyNames": {"enum": ["D1", "H4", "H1"]},
                  "additionalProperties": _DATA_REF},
    "missing_data": _STRS,
    "error": _null(_ERROR),
}

_COMMON_RULES = [
    {"if": {"properties": {"result_status": {"const": "ERROR"}}},
     "then": {"properties": {"error": _ERROR}},
     "else": {"properties": {"error": {"type": "null"}}}},
    {"if": {"properties": {"result_status": {"const": "INSUFFICIENT_DATA"}}},
     "then": {"properties": {"missing_data": {"minItems": 1}}}},
]


def _schema(specific: dict, required_specific: list[str], extra_rules: list | None = None,
            optional: dict | None = None) -> dict:
    props = {**COMMON, **specific, **(optional or {})}
    return {"type": "object", "additionalProperties": False,
            "required": list(COMMON) + required_specific, "properties": props,
            "allOf": _COMMON_RULES + (extra_rules or [])}


_CONDITION = {"type": "object", "additionalProperties": False,
              "required": ["condition_id", "description", "timeframe", "observed_value", "threshold", "operator", "satisfied"],
              "properties": {"condition_id": _STR, "description": _STR, "timeframe": _TF,
                             "observed_value": {"type": "number"}, "threshold": {"type": "number"},
                             "operator": {"enum": [">", ">=", "<", "<=", "=="]}, "satisfied": {"type": "boolean"}}}
_EXIT_MECH = {"type": "object", "additionalProperties": False,
              "required": ["type", "trigger_condition", "execution_method", "failure_procedure"],
              "properties": {"type": {"enum": ["STOP_LOSS", "TRAILING_STOP", "TARGET_PRICE"]},
                             "trigger_condition": _STR, "execution_method": _STR, "failure_procedure": _STR}}

# B.2
REGIME = _schema({
    "classifier_id": _STR, "regime_label": _STR, "candidate_label": _null(_STR), "previous_label": _null(_STR),
    "regime_since_utc": _null(_TS), "bars_in_regime": {"type": "integer", "minimum": 0},
    "measurements": {"type": "object", "additionalProperties": {"type": "number"}},
    "threshold_margins": {"type": "object", "additionalProperties": {"type": "number"}},
}, ["classifier_id", "regime_label", "candidate_label", "previous_label", "regime_since_utc",
    "bars_in_regime", "measurements"], [
    {"if": {"properties": {"result_status": {"enum": ["INSUFFICIENT_DATA", "ERROR"]}}},
     "then": {"properties": {"regime_label": {"const": "UNCLASSIFIED"}}}},
    {"if": {"properties": {"regime_label": {"const": "TRANSITION"}}},
     "then": {"properties": {"candidate_label": _STR}}},
])

# B.3
_PREDICTION = {"type": "object", "additionalProperties": False,
               "required": ["target", "horizon_bars", "timeframe", "value", "value_type"],
               "properties": {"target": _STR, "horizon_bars": {"type": "integer", "minimum": 1}, "timeframe": _TF,
                              "value": {"type": "number"}, "value_type": _STR}}
_DRIFT = {"type": "object", "additionalProperties": False,
          "required": ["psi_max", "expectancy_last20", "ic_lower_bound_oos", "suspended_reason"],
          "properties": {"psi_max": _null({"type": "number"}), "expectancy_last20": _null({"type": "number"}),
                         "ic_lower_bound_oos": _null({"type": "number"}), "suspended_reason": _null(_STR)}}
_MODEL_FIELDS = ("model_id", "model_version", "model_hash", "approval_ref", "feature_set_version", "features_hash")
ML = _schema({
    "inference_status": {"enum": ["INFERENCE_AVAILABLE", "NO_ACTIVE_MODEL", "MODEL_SUSPENDED"]},
    "model_id": _null(_STR), "model_version": _null(_STR), "model_hash": _null({"type": "string", "pattern": "^[0-9a-f]{64}$"}),
    "approval_ref": _null(_STR), "feature_set_version": _null(_SEMVER), "features_hash": _null(_STR),
    "prediction": _null(_PREDICTION), "drift": _null(_DRIFT), "advisory_only": {"const": True},
}, ["inference_status", *_MODEL_FIELDS, "prediction", "drift", "advisory_only"], [
    {"if": {"properties": {"inference_status": {"const": "INFERENCE_AVAILABLE"}}},
     "then": {"properties": {**{k: {"not": {"type": "null"}} for k in _MODEL_FIELDS}, "prediction": _PREDICTION}}},
    {"if": {"properties": {"inference_status": {"const": "NO_ACTIVE_MODEL"}}},
     "then": {"properties": {**{k: {"type": "null"} for k in _MODEL_FIELDS}, "prediction": {"type": "null"}}}},
    {"if": {"properties": {"inference_status": {"const": "MODEL_SUSPENDED"}}},
     "then": {"properties": {"prediction": {"type": "null"},
                             "drift": {"type": "object", "properties": {"suspended_reason": _STR},
                                       "required": ["suspended_reason"]}}}},
])

# B.4 + B.7.1
CANDIDATE_FIELDS = ("candidate_id", "candidate_type", "strategy_id", "strategy_version", "strategy_family",
                    "strategy_status", "operating_mode", "experiment_ref", "signal_timeframe",
                    "signal_bar_close_utc", "conditions", "entry_zone", "entry_reference_price", "stop_loss",
                    "take_profit", "exit_mechanism", "invalidation_conditions")
_CAND_PROPS = {
    "candidate_id": _UUID, "candidate_type": {"const": "ENTRY_LONG"}, "strategy_id": _STR,
    "strategy_version": _SEMVER,
    "strategy_family": {"enum": ["TREND_FOLLOWING", "MOMENTUM", "MEAN_REVERSION", "BREAKOUT", "VOLATILITY_BASED", "ML_BASED"]},
    "strategy_status": {"enum": ["APPROVED", "RESEARCH"]}, "operating_mode": {"enum": ["RESEARCH", "PAPER", "LIVE"]},
    "experiment_ref": _null(_STR), "signal_timeframe": _TF, "signal_bar_close_utc": _TS,
    "conditions": {"type": "array", "minItems": 1, "items": {**_CONDITION, "properties": {**_CONDITION["properties"], "satisfied": {"const": True}}}},
    "entry_zone": {"type": "object", "additionalProperties": False, "required": ["min", "max"],
                   "properties": {"min": _POS, "max": _POS}},
    "entry_reference_price": _POS,
    "stop_loss": {"type": "object", "additionalProperties": False, "required": ["price", "method", "parameters"],
                  "properties": {"price": _POS, "method": _STR, "parameters": {"type": "object"}}},
    "take_profit": _null(_POS), "exit_mechanism": _EXIT_MECH,
    "invalidation_conditions": {"type": "array", "minItems": 1, "items": _STR},
}
CANDIDATE = _schema({**_CAND_PROPS, "regime_message_id": _null(_UUID), "ml_inference_message_id": _null(_UUID)},
                    ["regime_message_id", "ml_inference_message_id"], [
    {"if": {"properties": {"result_status": {"const": "COMPLETED"}}},
     "then": {"required": list(CANDIDATE_FIELDS),
              "properties": {"regime_message_id": _UUID, "ml_inference_message_id": _UUID}},
     "else": {"not": {"anyOf": [{"required": [f]} for f in CANDIDATE_FIELDS]}}},
    {"if": {"properties": {"result_status": {"const": "COMPLETED"}, "strategy_status": {"const": "RESEARCH"}},
            "required": ["strategy_status"]},
     "then": {"properties": {"operating_mode": {"const": "RESEARCH"}}}},
    {"if": {"properties": {"strategy_status": {"const": "APPROVED"}}, "required": ["strategy_status"]},
     "then": {"properties": {"experiment_ref": _STR}}},
    {"if": {"properties": {"result_status": {"const": "ERROR"}}},
     "then": {"properties": {"error": {"required": ["code", "message", "stage", "upstream_message_id",
                                                    "strategy_id", "strategy_version"]}}}},
], optional=_CAND_PROPS)

# B.5
EXIT_SIGNAL = _schema({
    "exit_id": _UUID, "operation_id": _null(_UUID), "strategy_id": _STR, "strategy_version": _SEMVER,
    "exit_reason": {"enum": ["EXIT_CONDITION", "INVALIDATION", "TIME_EXIT"]},
    "conditions": {"type": "array", "items": _CONDITION}, "signal_timeframe": _TF,
    "signal_bar_close_utc": _TS, "reference_price": _POS, "supersedes_entry_candidates": {"type": "array", "items": _UUID},
}, ["exit_id", "operation_id", "strategy_id", "strategy_version", "exit_reason", "conditions",
    "signal_timeframe", "signal_bar_close_utc", "reference_price", "supersedes_entry_candidates"])

# B.6
STOP_ADJUSTMENT = _schema({
    "request_id": _UUID, "operation_id": _null(_UUID), "strategy_id": _STR, "strategy_version": _SEMVER,
    "current_stop": _POS, "requested_stop": _POS, "method": _STR, "parameters": {"type": "object"},
    "signal_timeframe": _TF, "signal_bar_close_utc": _TS,
}, ["request_id", "operation_id", "strategy_id", "strategy_version", "current_stop", "requested_stop",
    "method", "parameters", "signal_timeframe", "signal_bar_close_utc"])

# B.7
NO_SETUP_REASONS = ("NO_CANDIDATE", "NO_APPROVED_STRATEGY", "MULTIPLE_ENTRY_CANDIDATES", "EXIT_SIGNAL_PRIORITY",
                    "PRE_PHASE3_BLOCK", "UPSTREAM_INSUFFICIENT_DATA")
PRE_PHASE3_DETAILS = ("OPEN_POSITION", "LOSS_STREAK_LOCK", "MONTHLY_DRAWDOWN_LOCK", "MONTHLY_TRADE_LIMIT_LOCK",
                      "DATA_UNAVAILABLE", "EXCHANGE_DESYNC", "MANUAL_REVIEW", "SAFE_MODE", "AI_BUDGET_CAP")
DISCARD_REASONS = ("CONFLICT_MULTIPLE_ENTRIES", "SUPERSEDED_BY_EXIT", "NOT_ELIGIBLE_ML_UNAVAILABLE", "NOT_ELIGIBLE_REGIME")
NO_SETUP = _schema({
    "reason_code": {"enum": list(NO_SETUP_REASONS)}, "reason_detail": _null(_STR),
    "evaluated_strategies": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["strategy_id", "strategy_version", "result", "failed_conditions"],
        "properties": {"strategy_id": _STR, "strategy_version": _SEMVER,
                       "result": {"enum": ["NO_SIGNAL", "CANDIDATE", "DISCARDED", "NOT_ELIGIBLE"]},
                       "failed_conditions": _STRS}}},
    "discarded_candidates": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["candidate_id", "strategy_id", "strategy_version", "discard_reason"],
        "properties": {"candidate_id": _null(_UUID), "strategy_id": _STR, "strategy_version": _SEMVER,
                       "discard_reason": {"enum": list(DISCARD_REASONS)}}}},
    "exit_signal_ref": _null(_UUID), "llm_calls": {"const": 0},
}, ["reason_code", "reason_detail", "evaluated_strategies", "discarded_candidates", "exit_signal_ref", "llm_calls"], [
    {"if": {"properties": {"reason_code": {"const": "PRE_PHASE3_BLOCK"}}},
     "then": {"properties": {"reason_detail": {"enum": list(PRE_PHASE3_DETAILS)}}}},
    {"if": {"properties": {"reason_code": {"const": "EXIT_SIGNAL_PRIORITY"}}},
     "then": {"properties": {"exit_signal_ref": _UUID}}},
    {"properties": {"result_status": {"enum": ["COMPLETED", "INSUFFICIENT_DATA"]}}},   # errores técnicos: no NO_SETUP
])

SCHEMAS = {"REGIME_CLASSIFIED": REGIME, "ML_INFERENCE_COMPLETED": ML, "STRATEGY_CANDIDATE": CANDIDATE,
           "STRATEGY_EXIT_SIGNAL": EXIT_SIGNAL, "STOP_ADJUSTMENT_REQUESTED": STOP_ADJUSTMENT, "NO_SETUP": NO_SETUP}
_VALIDATORS = {}
for _t, _s in SCHEMAS.items():
    Draft202012Validator.check_schema(_s)
    _VALIDATORS[_t] = Draft202012Validator(_s)


class EnginePayloadError(ValueError):
    pass


def validate_engine_payload(message_type: str, payload: Any) -> None:
    """TC-MSG-004. Además de JSON Schema: stop < entrada, entrada dentro de la zona,
    requested_stop > current_stop (B.4, B.6)."""
    v = _VALIDATORS.get(message_type)
    if v is None:
        raise EnginePayloadError(f"sin esquema de motor para {message_type}")
    errs = sorted(v.iter_errors(payload), key=lambda e: list(e.path))
    if errs:
        raise EnginePayloadError("; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs[:5]))
    if message_type == "STRATEGY_CANDIDATE" and payload["result_status"] == "COMPLETED":
        z, ref, sl = payload["entry_zone"], payload["entry_reference_price"], payload["stop_loss"]["price"]
        if not (z["min"] <= ref <= z["max"]) or not sl < z["min"]:
            raise EnginePayloadError("candidato incoherente: entrada fuera de la zona o stop ≥ zona")
        tp = payload["take_profit"]
        if tp is not None and tp <= z["max"]:
            raise EnginePayloadError("candidato incoherente: take_profit ≤ zona de entrada")
    if message_type == "STOP_ADJUSTMENT_REQUESTED" and not payload["requested_stop"] > payload["current_stop"]:
        raise EnginePayloadError("INVALID_STOP_REQUEST: requested_stop debe ser > current_stop (INV-009)")


def schema_copy(message_type: str) -> dict:
    return copy.deepcopy(SCHEMAS[message_type])
