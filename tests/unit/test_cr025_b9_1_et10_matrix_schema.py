"""B9.1 (CR-025 v1.13): V9 en la matriz de ET-10 y código ELIGIBILITY_UNDETERMINED en el esquema del motor.
No prueba el cableado del Strategy Engine (B9.4)."""
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from swingpilot.engines import schemas as S  # noqa: E402
from swingpilot.engines.common import base_payload  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402


def test_et10_matrix_has_v9_and_et8_et9_preserved():
    assert I.STAGES["ET-10"] == ("V2", "V3", "V4post", "V5", "V8", "V9")
    assert I.STAGES["ET-9"] == ("V2", "V3", "V4post", "V5", "V8", "V9")
    assert I.STAGES["ET-8"] == ("V1b", "V2", "V3", "V4post", "V5", "V6", "V7m", "V7d", "V8")
    assert "V9" not in I.STAGES["ET-8"]
    assert all("V9" not in v for k, v in I.STAGES.items() if k not in ("ET-9", "ET-10"))


def _err_payload(code, stage="STRATEGY_EVALUATION"):
    p = base_payload("strategy_engine", "1.0.0", None, "ERROR", {}, error={
        "code": code, "message": "V9: x", "stage": stage, "upstream_message_id": None,
        "strategy_id": "s1", "strategy_version": "1.0.0"})
    p.update(regime_message_id=str(uuid.uuid4()), ml_inference_message_id=str(uuid.uuid4()))
    return p


def test_eligibility_undetermined_accepted_in_error_schema():
    assert "ELIGIBILITY_UNDETERMINED" in S.ERROR_CODES
    S.validate_engine_payload("STRATEGY_CANDIDATE", _err_payload("ELIGIBILITY_UNDETERMINED"))


def test_unknown_error_code_still_rejected():
    with pytest.raises(S.EnginePayloadError):
        S.validate_engine_payload("STRATEGY_CANDIDATE", _err_payload("ELIGIBILITY_UNKNOWN"))


@pytest.mark.parametrize("detail", ["NONE_APPROVED", "CONFIRMATORY_ELIGIBILITY_LOST"])
def test_no_approved_strategy_contract_details_schema_compatible(detail):
    p = base_payload("strategy_engine", "1.0.0", None, "COMPLETED", {})
    p.update(reason_code="NO_APPROVED_STRATEGY", reason_detail=detail, evaluated_strategies=[
        {"strategy_id": "s1", "strategy_version": "1.0.0", "result": "NOT_ELIGIBLE", "failed_conditions": ["x"]}],
        discarded_candidates=[], exit_signal_ref=None, llm_calls=0)
    S.validate_engine_payload("NO_SETUP", p)
