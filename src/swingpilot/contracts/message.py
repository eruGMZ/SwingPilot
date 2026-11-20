"""Contrato universal de mensajes (REQ-G-060, REQ-G-061; api_contracts.md §1).

Los 33 tipos de evento provienen del catálogo de api_contracts.md §2
(un test verifica que coinciden con el documento).
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from jsonschema import Draft202012Validator

from .versioning import check_compatibility

CONTRACT_SCHEMA_VERSION = "1.0.0"  # versión inicial del esquema de mensaje (implementación)

EVENT_TYPES = (
    "ANALYSIS_REQUESTED", "MARKET_ANALYSIS_COMPLETED", "MACRO_ANALYSIS_COMPLETED",
    "ML_INFERENCE_COMPLETED", "REGIME_CLASSIFIED", "STRATEGY_CANDIDATE",
    "DECISION_SYNTHESIS_COMPLETED", "TRADE_PROPOSAL", "RISK_APPROVED",
    "RISK_REJECTED", "RISK_REQUIRES_REVIEW", "ORDER_SUBMITTED",
    "ORDER_PARTIALLY_FILLED", "ORDER_FILLED", "ORDER_CANCELLED", "ORDER_REJECTED",
    "STOP_ORDER_PLACED", "STOP_ORDER_REPLACED", "STOP_ORDER_FAILED",
    "STARTUP_RECONCILIATION_COMPLETED", "AUTHORIZATION_INVALIDATED",
    "UNAUTHORIZED_APPROVAL_ATTEMPT", "NO_SETUP", "RISK_ANALYSIS_COMPLETED",
    "HEARTBEAT", "PUBLIC_IP_CHANGED", "OPERATION_STATE_CHANGED",
    "AUTHORIZATION_EXPIRED", "AI_BUDGET_WARNING", "PROTECTIVE_CLOSE_SUBMITTED",
    "STRATEGY_ANALYSIS_COMPLETED",  # CR-015
    "STRATEGY_EXIT_SIGNAL", "STOP_ADJUSTMENT_REQUESTED",  # CR-018
)

_UUID4 = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
_SEMVER = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
# ISO 8601 en UTC (sufijo Z), con fracción opcional.
_TS = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
_COMPONENT = {"type": "string", "minLength": 1}

MESSAGE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "SwingPilot universal message",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "message_id", "correlation_id", "causation_id", "schema_version", "source",
        "destination", "message_type", "timestamp_utc", "data_timestamp_utc",
        "asset", "timeframe", "payload", "status",
    ],
    "properties": {
        "message_id": {"type": "string", "pattern": _UUID4},
        "correlation_id": {"type": "string", "pattern": _UUID4},
        "causation_id": {"anyOf": [{"type": "string", "pattern": _UUID4}, {"type": "null"}]},
        "schema_version": {"type": "string", "pattern": _SEMVER},
        "source": _COMPONENT,
        "destination": _COMPONENT,
        "message_type": {"enum": list(EVENT_TYPES)},
        "timestamp_utc": {"type": "string", "pattern": _TS},
        "data_timestamp_utc": {"type": "string", "pattern": _TS},
        "asset": {"const": "BTC/USDT"},  # solo BTC/USDT (DEC-002)
        "timeframe": {"enum": ["D1", "H4", "H1", None]},
        "payload": {"type": "object"},
        "status": {"enum": ["PENDING", "PROCESSING", "COMPLETED", "FAILED"]},
    },
}

_VALIDATOR = Draft202012Validator(MESSAGE_SCHEMA)


class MessageValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_message(message: Any, supported_version: str = CONTRACT_SCHEMA_VERSION) -> None:
    """Valida esquema y compatibilidad de versión. Lanza MessageValidationError
    o SchemaVersionError; el mensaje inválido no debe procesarse (Fail-Closed)."""
    errs = sorted(_VALIDATOR.iter_errors(message), key=lambda e: list(e.path))
    if errs:
        raise MessageValidationError(
            [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs]
        )
    _check_timestamps(message)
    check_compatibility(message["schema_version"], supported_version)


def _check_timestamps(message: dict) -> None:
    bad = []
    for k in ("timestamp_utc", "data_timestamp_utc"):
        try:
            datetime.fromisoformat(message[k].replace("Z", "+00:00"))
        except ValueError:
            bad.append(f"{k}: fecha/hora inválida")
    if bad:
        raise MessageValidationError(bad)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def new_message(
    *, source: str, destination: str, message_type: str, data_timestamp_utc: str,
    payload: dict, timeframe: str | None = None, status: str = "PENDING",
    correlation_id: str | None = None, causation_id: str | None = None,
    asset: str = "BTC/USDT",
) -> dict:
    """Construye y valida un mensaje. Sin correlation_id propio genera uno nuevo
    (mensaje origen); con causation_id el llamador debe heredar el correlation_id
    del mensaje padre (ver derive_message)."""
    msg = {
        "message_id": str(uuid.uuid4()),
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "causation_id": causation_id,
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "source": source, "destination": destination, "message_type": message_type,
        "timestamp_utc": _now(), "data_timestamp_utc": data_timestamp_utc,
        "asset": asset, "timeframe": timeframe, "payload": payload, "status": status,
    }
    validate_message(msg)
    return msg


def derive_message(parent: dict, **kwargs) -> dict:
    """Mensaje causado por `parent`: hereda correlation_id y fija causation_id
    al message_id del padre (REQ-G-061, REQ-G-062)."""
    return new_message(
        correlation_id=parent["correlation_id"], causation_id=parent["message_id"], **kwargs
    )
