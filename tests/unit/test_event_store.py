"""FEAT-003 — TC-MSG-003, TC-SEC-004, TC-AC-04 (parte de mensajes), REQ-G-062."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.audit import EventStore, EventStoreError  # noqa: E402
from swingpilot.contracts import MessageValidationError, derive_message, new_message  # noqa: E402

TS = "2026-11-19T12:00:00Z"
K = dict(data_timestamp_utc=TS, payload={})


def root():
    return new_message(source="trading_engine", destination="ai_orchestrator",
                       message_type="ANALYSIS_REQUESTED", timeframe="H4", **K)


def child(parent, mt="MARKET_ANALYSIS_COMPLETED"):
    return derive_message(parent, source="ai_orchestrator", destination="x", message_type=mt, **K)


@pytest.fixture
def store(tmp_path):
    s = EventStore(tmp_path / "audit.db")
    yield s
    s.close()


def test_append_and_reconstruct_chain_in_order(store):
    r = root(); a = child(r); b = child(a, "DECISION_SYNTHESIS_COMPLETED")
    for m in (r, a, b):
        assert store.append(m) is True
    rep = store.get_chain(r["correlation_id"])
    assert [m["message_id"] for m in rep.messages] == [r["message_id"], a["message_id"], b["message_id"]]
    assert rep.complete and rep.roots == [r["message_id"]] and rep.orphans == []
    assert rep.messages[0] == r  # contenido íntegro


def test_chains_are_isolated_by_correlation_id(store):
    r1, r2 = root(), root()
    store.append(r1); store.append(r2); store.append(child(r1))
    assert len(store.get_chain(r1["correlation_id"]).messages) == 2
    assert len(store.get_chain(r2["correlation_id"]).messages) == 1


def test_append_is_idempotent(store):
    r = root()
    assert store.append(r) is True
    assert store.append(r) is False
    assert store.count() == 1


def test_same_id_different_content_rejected(store):
    r = root(); store.append(r)
    tampered = dict(r, payload={"alterado": True})
    with pytest.raises(EventStoreError):
        store.append(tampered)
    assert store.get_chain(r["correlation_id"]).messages[0]["payload"] == {}


def test_invalid_message_not_stored(store):
    r = root(); del r["correlation_id"]
    with pytest.raises(MessageValidationError):
        store.append(r)
    assert store.count() == 0


def test_missing_parent_is_reported_as_orphan(store):
    r = root(); a = child(r)
    store.append(a)  # el padre nunca se registró
    rep = store.get_chain(a["correlation_id"])
    assert rep.orphans == [a["message_id"]] and not rep.complete


def test_empty_chain_is_not_complete(store):
    assert not store.get_chain("00000000-0000-4000-8000-000000000000").complete


# TC-SEC-004
def test_update_and_delete_are_prohibited(tmp_path):
    path = tmp_path / "audit.db"
    s = EventStore(path); r = root(); s.append(r); s.close()
    raw = sqlite3.connect(path)
    with pytest.raises(sqlite3.DatabaseError, match="inmutable"):
        raw.execute("UPDATE audit_events SET message_type='RISK_APPROVED'")
    with pytest.raises(sqlite3.DatabaseError, match="inmutable"):
        raw.execute("DELETE FROM audit_events")
    assert raw.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 1
    raw.close()


def test_persistence_across_reopen(tmp_path):
    path = tmp_path / "audit.db"
    s = EventStore(path); r = root(); s.append(r); s.close()
    s2 = EventStore(path)
    assert s2.get_chain(r["correlation_id"]).messages == [r]
    s2.close()
