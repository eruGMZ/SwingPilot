"""CR-024 v1.12 CR24-I2b — WINDOW_RESULT_PERSISTED: validación del registro (sintético, sin orquestación)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research.result_serialization import canonical_bytes, evaluation_hash  # noqa: E402
from swingpilot.research.result_store import ResultStore  # noqa: E402

EID, PRE, MAN = "EXP-0001", "a" * 64, "b" * 64
def _lines(recs):
    return b"".join(X._serialize(r) + b"\n" for r in recs)


def _base(snapshot):
    return [
        {"kind": "CREATED", "experiment_id": EID, "title": "t", "state": "IDEA", "actor": "x", "at_utc": "t"},
        {"kind": "TRANSITION", "experiment_id": EID, "from": "DESIGN", "to": "PREREGISTERED", "actor": "x",
         "evidence": {"preregistration_sha256": PRE}, "reason": "", "at_utc": "t"},
        {"kind": "PARTITION_CONSUMED", "snapshot_id": snapshot, "partition": "oos", "experiment_id": EID,
         "snapshot_last_open_time": 1, "decision_ref": "DEC-001.md", "actor": "propietario", "at_utc": "t"},
    ]


@pytest.fixture
def env(tmp_path):
    snap = "SNAP-0001"
    reg = X.ExperimentRegistry(tmp_path / "registry.jsonl")
    recs = _base(snap)
    reg.path.write_bytes(_lines(recs))
    store = ResultStore(tmp_path / "results")
    cons_sha = X._line_sha(X._serialize(recs[2]))
    doc = {"schema": 1, "experiment_id": EID, "partition": "oos", "prereg_sha256": PRE, "snapshot_id": snap,
           "window_id": f"{EID}/OOS", "manifest_sha256": MAN,
           "consumption": {"decision_ref": "DEC-001.md", "consumed_line_sha256": cons_sha},
           "evaluator_version": "v-test", "outcome": {"partition": "oos", "verdict": "ELIGIBLE_FOR_HUMAN_REVIEW",
                                                       "nature": None, "eligibility": "ELIGIBLE", "reasons": [],
                                                       "metrics": None}}
    data = canonical_bytes(doc)
    store.write(EID, "oos", data)
    return reg, store, recs, data, snap


def _append(reg, rec):
    reg.path.write_bytes(reg.path.read_bytes() + X._serialize(rec) + b"\n")


def _mk(reg, store, **over):
    """Marcador derivado de la evidencia (como lo hace persist_window_result); se añade a mano en estas pruebas."""
    from swingpilot.research.result_serialization import parse_strict
    data = store.read(EID, "oos")
    doc = parse_strict(data)
    m = {"at_utc": "t", "kind": X.RESULT_KIND, "experiment_id": EID, "partition": "oos",
         "snapshot_id": doc["snapshot_id"], "evaluation_hash": evaluation_hash(data), "prereg_sha256": PRE,
         "verdict": doc["outcome"]["verdict"], "eligibility": doc["outcome"]["eligibility"],
         "evaluator_version": "v-test", "consumed_line_sha256": doc["consumption"]["consumed_line_sha256"],
         "actor": "s"}
    return {**m, **over}


def test_valid_marker_loads_and_verifies_and_consumption_shape_intact(env):
    reg, store, recs, data, snap = env
    m = _mk(reg, store)
    _append(reg, m)
    assert reg.verified_window_results(store) == [m] and reg.consumed_partitions() == [recs[2]]
    assert reg.window_result_state(store, EID, "oos") == "RESULT_VALID"


def test_byte_identical_duplicate_marker_is_the_same_result(env):
    reg, store, *_ = env
    m = _mk(reg, store)
    _append(reg, m)
    _append(reg, m)                                          # B.5: copia idéntica = el mismo resultado
    assert reg.window_results() == [m]


@pytest.mark.parametrize("over", [
    {"consumed_line_sha256": "c" * 64}, {"prereg_sha256": "d" * 64}, {"partition": "OOS"},
    {"partition": "lockbox"}, {"experiment_id": "EXP-0002"}, {"snapshot_id": "SNAP-0002"},
    {"evaluation_hash": "xyz"}, {"actor": ""}, {"extra": 1},
])
def test_corrupt_marker_blocks_loading(env, over):
    reg, store, *_ = env
    m = _mk(reg, store, **over)
    _append(reg, m)
    with pytest.raises(X.RegistryCorruptError):
        reg.records()


def test_marker_before_consumption_or_conflicting_duplicate_is_corrupt(env):
    reg, store, recs, *_ = env
    m = _mk(reg, store)
    reg.path.write_bytes(_lines(recs[:2]) + X._serialize(m) + b"\n" + X._serialize(recs[2]) + b"\n")
    with pytest.raises(X.RegistryCorruptError):
        reg.records()
    reg.path.write_bytes(_lines(recs))
    _append(reg, m)
    _append(reg, {**m, "actor": "otro"})
    with pytest.raises(X.RegistryCorruptError):
        reg.records()


def test_duplicate_consumption_and_ambiguous_prereg_invalidate_marker(env):
    reg, store, recs, *_ = env
    m = _mk(reg, store)
    for bad in (recs + [recs[2]], recs[:2] + [recs[1]] + recs[2:]):
        reg.path.write_bytes(_lines(bad))
        _append(reg, m)
        with pytest.raises(X.RegistryCorruptError):
            reg.records()


def test_marker_kind_cannot_be_written_through_generic_api(env):
    reg, store, *_ = env
    before = reg.path.read_bytes()
    with pytest.raises(X.ExperimentError):
        reg._append(_mk(reg, store))
    assert reg.path.read_bytes() == before


@pytest.mark.parametrize("tamper", ["delete", "bytes", "symlink", "fields"])
def test_evidence_tamper_is_detected_on_authoritative_reads(env, tamper, tmp_path):
    reg, store, recs, data, snap = env
    _append(reg, _mk(reg, store))
    f = store.root / EID / "oos.result.json"
    f.chmod(0o644)
    if tamper == "delete":
        f.unlink()
    elif tamper == "bytes":
        f.write_bytes(canonical_bytes({"a": 1}))
    elif tamper == "symlink":
        other = tmp_path / "o.json"
        other.write_bytes(data)
        f.unlink()
        f.symlink_to(other)
    else:
        doc = json.loads(data)
        doc["outcome"]["verdict"] = "REJECTED"
        f.write_bytes(canonical_bytes(doc))
    for call in (lambda: reg.verified_window_results(store), lambda: reg.window_result_state(store, EID, "oos"),
                 lambda: reg.window_result_favorable(store, EID, "oos")):
        with pytest.raises(X.RegistryCorruptError):
            call()


def test_reconciliation_states_and_no_automatic_recovery(env):
    reg, store, recs, data, snap = env
    before = reg.path.read_bytes()
    assert reg.window_result_state(store, EID, "oos") == "EVIDENCE_ONLY"
    assert reg.window_result_state(store, EID, "lockbox") == "NOT_CONSUMED"
    assert reg.path.read_bytes() == before                    # solo lectura: nada se escribe ni repara
    (store.root / EID / "oos.result.json").chmod(0o644)
    (store.root / EID / "oos.result.json").unlink()
    assert reg.window_result_state(store, EID, "oos") == "CONSUMED_NO_RESULT"
    _append(reg, {"at_utc": "t", "kind": X.RESULT_KIND, "experiment_id": EID, "partition": "oos",
                                  "snapshot_id": snap, "evaluation_hash": "e" * 64, "prereg_sha256": PRE,
                                  "verdict": "v", "eligibility": None, "evaluator_version": "v",
                                  "consumed_line_sha256": X._line_sha(X._serialize(recs[2])), "actor": "s"})
    with pytest.raises(X.RegistryCorruptError):               # marcador sin evidencia
        reg.window_result_state(store, EID, "oos")


def test_evidence_not_bound_to_consumption_is_corrupt(env):
    reg, store, recs, data, snap = env
    reg.path.write_bytes(_lines(recs[:2]))                    # evidencia sin consumo previo
    with pytest.raises(X.RegistryCorruptError):
        reg.window_result_state(store, EID, "oos")


def test_favorable_authoritative_predicate(env, tmp_path):
    reg, store, recs, data, snap = env
    assert reg.window_result_favorable(store, EID, "oos") is False        # EVIDENCE_ONLY no es favorable
    _append(reg, _mk(reg, store))
    assert reg.window_result_favorable(store, EID, "oos") is True
    for k, v in (("verdict", "REJECTED"), ("eligibility", "NOT_ELIGIBLE"), ("nature", "TECHNICAL")):
        doc = json.loads(data)
        doc["outcome"][k] = v
        d2 = canonical_bytes(doc)
        other = ResultStore(tmp_path / f"r-{k}")
        other.write(EID, "oos", d2)
        reg.path.write_bytes(_lines(recs))
        _append(reg, _mk(reg, other))
        assert reg.window_result_favorable(other, EID, "oos") is False
