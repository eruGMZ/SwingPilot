"""FEAT-001 / FEAT-002 — TC-MSG-001, TC-MSG-002, TC-MSG-003, TC-AC-02, TC-AC-03, TC-AC-15 (parcial)."""
import copy
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swingpilot.contracts import (  # noqa: E402
    CONTRACT_SCHEMA_VERSION, EVENT_TYPES, MessageValidationError,
    SchemaVersionError, check_compatibility, derive_message, new_message, validate_message,
)

TS = "2026-11-19T12:00:00Z"


def make(**kw):
    base = dict(source="trading_engine", destination="ai_orchestrator",
                message_type="ANALYSIS_REQUESTED", data_timestamp_utc=TS,
                payload={"x": 1}, timeframe="H4")
    base.update(kw)
    return new_message(**base)


def test_valid_message_roundtrip():
    m = make()
    validate_message(m)
    assert m["schema_version"] == CONTRACT_SCHEMA_VERSION
    assert m["causation_id"] is None


# TC-MSG-001
def test_missing_correlation_id_is_rejected():
    m = make()
    del m["correlation_id"]
    with pytest.raises(MessageValidationError) as e:
        validate_message(m)
    assert "correlation_id" in str(e.value)


@pytest.mark.parametrize("field", [
    "message_id", "causation_id", "schema_version", "source", "destination",
    "message_type", "timestamp_utc", "data_timestamp_utc", "asset", "timeframe",
    "payload", "status"])
def test_each_required_field_is_enforced(field):
    m = make()
    del m[field]
    with pytest.raises(MessageValidationError):
        validate_message(m)


@pytest.mark.parametrize("field,value", [
    ("correlation_id", "no-es-uuid"), ("message_id", "123"),
    ("message_type", "INVENTED_EVENT"), ("status", "DONE"),
    ("asset", "ETH/USDT"), ("timeframe", "M5"),
    ("timestamp_utc", "2026-11-19 12:00:00"), ("timestamp_utc", "2026-13-45T99:00:00Z"),
    ("data_timestamp_utc", "2026-11-19T12:00:00+05:00"),
    ("payload", "texto libre"), ("source", ""),
])
def test_invalid_values_are_rejected(field, value):
    m = make()
    m[field] = value
    with pytest.raises(MessageValidationError):
        validate_message(m)


def test_extra_fields_are_rejected():
    m = make()
    m["extra"] = 1
    with pytest.raises(MessageValidationError):
        validate_message(m)


def test_non_dict_is_rejected():
    with pytest.raises(MessageValidationError):
        validate_message("texto libre")


# TC-MSG-002 / FEAT-002
def test_incompatible_major_version_rejected():
    m = make()
    m["schema_version"] = "2.0.0"
    with pytest.raises(SchemaVersionError):
        validate_message(m)
    m["schema_version"] = "0.9.0"
    with pytest.raises(SchemaVersionError):
        validate_message(m)


def test_compatible_minor_patch_accepted():
    m = make()
    m["schema_version"] = "1.7.3"
    validate_message(m)


@pytest.mark.parametrize("bad", ["1", "1.0", "v1.0.0", "1.0.0-beta", "", None, 1])
def test_malformed_version_rejected(bad):
    with pytest.raises((SchemaVersionError, MessageValidationError)):
        check_compatibility(bad, "1.0.0")


# TC-MSG-003 / TC-AC-03
def test_correlation_and_causation_chain():
    root = make()
    c1 = derive_message(root, source="ai_orchestrator", destination="market_analyst",
                        message_type="MARKET_ANALYSIS_COMPLETED", data_timestamp_utc=TS, payload={})
    c2 = derive_message(c1, source="ai_orchestrator", destination="decision_synthesis",
                        message_type="DECISION_SYNTHESIS_COMPLETED", data_timestamp_utc=TS, payload={})
    chain = [root, c1, c2]
    assert len({m["correlation_id"] for m in chain}) == 1
    assert c1["causation_id"] == root["message_id"]
    assert c2["causation_id"] == c1["message_id"]
    assert len({m["message_id"] for m in chain}) == 3


def test_new_root_messages_get_distinct_correlation_ids():
    assert make()["correlation_id"] != make()["correlation_id"]


# Catálogo = api_contracts.md §2 (TC-AC-02 / REQ-G-063)
def test_event_catalog_matches_contract_document():
    text = (ROOT / "implementation" / "api_contracts.md").read_text(encoding="utf-8")
    section = text.split("## 2. Catálogo de Tipos de Eventos")[1].split("**Identificador de cliente")[0]
    documented = re.findall(r"^\| ([A-Z_]+) \|", section, flags=re.M)
    assert tuple(documented) == EVENT_TYPES
    assert len(EVENT_TYPES) == 33  # CR-018
