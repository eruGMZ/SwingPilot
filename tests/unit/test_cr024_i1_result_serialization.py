"""CR-024 v1.12 CR24-I1 — serialización canónica, evaluation_hash e IssuedWindowResult (sintético)."""
import copy
import dataclasses
import pickle
import re
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swingpilot.research import result_serialization as RS  # noqa: E402
from swingpilot.research import window_evaluation as W  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402

C = RS.canonical_bytes


def test_f64_tagging_and_signed_zero_nan_inf():
    assert C(1.0) == b'{"$f64":"3ff0000000000000"}'
    assert C(0.0) != C(-0.0) and C(-0.0) == b'{"$f64":"8000000000000000"}'
    assert C(float("nan")) == C(np.float64("nan")) == b'{"$f64":"7ff8000000000000"}'
    assert C(np.float32(0.5)) == C(0.5)
    for bad in (float("inf"), -float("inf")):
        with pytest.raises(RS.ResultSerializationError):
            C(bad)


def test_bool_int_str_distinct_and_numpy_int():
    assert C([True, 1, "1", np.int64(7), None]) == b'[true,1,"1",7,null]'
    assert C({"$": "x"}) != C({"$": 1})
    assert C("$f64") == b'"$f64"' and C(1.0) != C("3ff0000000000000")


def test_rejected_types_and_reserved_key():
    import datetime, decimal
    import pandas as pd
    for bad in (pd.Timestamp("2026-01-01"), np.array([1]), decimal.Decimal(1), b"x", {1}, {1: 2},
                datetime.date(2026, 1, 1), {"a": {"$f64": "3ff0000000000000"}}, object()):
        with pytest.raises(RS.ResultSerializationError):
            C(bad)


def test_dict_ordering_and_hash_stable():
    assert C({"b": 1, "a": 2}) == C({"a": 2, "b": 1}) == b'{"a":2,"b":1}'
    assert RS.evaluation_hash(C({"a": 1})) == RS.evaluation_hash(C({"a": 1}))
    assert re.fullmatch(r"[0-9a-f]{64}", RS.evaluation_hash(b"x"))


def test_strict_reading_roundtrip_and_rejections():
    ok = C({"x": [1.5, None, "é"], "y": True})
    assert RS.parse_strict(ok) == {"x": [{"$f64": "3ff8000000000000"}, None, "é"], "y": True}
    for bad in (b'{"a":1.0}', b'{"a":1e2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1,"a":2}',
                b'{"a": 1}', b'{"b":1,"a":2}', b'{"a":{"$f64":"7ff8000000000001"}}',
                b'{"a":{"$f64":"7ff0000000000000"}}', b'{"a":{"$f64":"3FF0000000000000"}}',
                b'{"a":{"$f64":"3ff0000000000000","b":1}}', b'{"a":"\\u00e9"}'):
        with pytest.raises(RS.ResultSerializationError):
            RS.parse_strict(bad)


def test_evaluator_version_system_derived_nonempty():
    v = RS.evaluator_version()
    assert v and "contract=1.12" in v and "schema=1" in v and "pyarrow=" in v


def _outcome(**kw):
    base = dict(partition="oos", verdict="INCONCLUSIVE", nature=None, eligibility=I.ELIGIBLE, reasons=["r"],
                metrics={"sharpe": 1.25}, trades=3)
    return W.WindowOutcome(**{**base, **kw})


BIND = dict(experiment_id="EXP-0001", prereg_sha256="a" * 64, snapshot_id="S", window_id="w/oos",
            manifest_sha256="b" * 64, decision_ref="DEC-1.md", consumed_line_sha256="c" * 64)


def test_document_fields_exact_and_excludes_at_actor():
    doc, raw = RS.build_document(_outcome(), **BIND)
    assert set(doc) == {"schema", "experiment_id", "partition", "prereg_sha256", "snapshot_id", "window_id",
                        "manifest_sha256", "consumption", "evaluator_version", "outcome"}
    assert set(doc["outcome"]) == {f.name for f in dataclasses.fields(W.WindowOutcome)}
    assert b"at_utc" not in raw and b"actor" not in raw
    assert RS.parse_strict(raw) == doc


def test_build_document_rejects_bad_binding_and_unserializable_outcome():
    with pytest.raises(RS.ResultSerializationError):
        RS.build_document(_outcome(), **{**BIND, "prereg_sha256": "A" * 64})
    with pytest.raises(RS.ResultSerializationError):
        RS.build_document(_outcome(metrics={"x": float("inf")}), **BIND)


def test_issued_result_opaque_immutable_not_forgeable():
    doc, raw = RS.build_document(_outcome(), **BIND)
    with pytest.raises(RS.ResultSerializationError):
        RS.IssuedWindowResult(object(), _outcome(), doc, raw, ())
    r = RS.issue(RS._ISSUE_KEY, _outcome(), doc, raw, ("e",))
    assert type(r) is RS.IssuedWindowResult and r.evaluation_hash == RS.evaluation_hash(raw)
    for op in (lambda: setattr(r, "evaluation_hash", "x"), lambda: copy.copy(r), lambda: copy.deepcopy(r),
               lambda: pickle.dumps(r)):
        with pytest.raises((AttributeError, RS.ResultSerializationError)):
            op()


def test_issue_credential_only_referenced_by_window_evaluation():
    src = Path(__file__).resolve().parents[2] / "src"
    for f in src.rglob("*.py"):
        if f.name not in ("result_serialization.py", "window_evaluation.py"):
            assert "_ISSUE_KEY" not in f.read_text(encoding="utf-8") and "RS.issue(" not in f.read_text(encoding="utf-8")


def test_issue_window_result_serialization_failure_is_technical(monkeypatch):
    """Resultado no canonicalizable pero con ligadura genuina → TECHNICAL/UNDETERMINABLE, metrics None, emitido."""
    class Prov:
        consumption = '{"kind": "PARTITION_CONSUMED"}'
        grant = ("EXP-0001", "oos", "S", "DEC-1.md", "p")
    rec = {"kind": "PARTITION_CONSUMED"}

    class Reg:
        def _load(self):
            return [b"line"], [rec]
    data = type("D", (), {"provenance": Prov()})()
    manifest = {"snapshot_id": "S", "window_id": "w/oos"}
    monkeypatch.setattr(W, "_check_evidence", lambda *a: None)
    monkeypatch.setattr(W.PR, "_preregistered_sha", lambda r, e: "a" * 64)
    bad = _outcome(metrics={"x": object()})
    monkeypatch.setattr(W, "_manifest_file_sha", lambda m, d: "b" * 64)
    oc, issued = W._issue(bad, data, manifest, Reg(), "EXP-0001")
    assert (oc.verdict, oc.nature, oc.eligibility, oc.metrics) == ("INCONCLUSIVE", "TECHNICAL", I.UNDETERMINABLE, None)
    assert issued is not None and issued.outcome is oc and not oc.retry_allowed
    good, issued2 = W._issue(_outcome(), data, manifest, Reg(), "EXP-0001")
    assert good.metrics == {"sharpe": 1.25} and RS.parse_strict(issued2.document_bytes)["outcome"]["trades"] == 3
    assert issued2.evaluation_hash == RS.evaluation_hash(issued2.document_bytes)


def test_no_issue_without_genuine_provenance():
    oc = _outcome()
    data = type("D", (), {"provenance": None, "partition": "oos"})()
    out, issued = W._issue(oc, data, {"snapshot_id": "S", "window_id": "w"}, None, "EXP-0001")
    assert out is oc and issued is None


def test_issue_requires_private_credential():
    doc, raw = RS.build_document(_outcome(), **BIND)
    for key in (None, object(), "k"):
        with pytest.raises(RS.ResultSerializationError):
            RS.issue(key, _outcome(), doc, raw, ("e",))
    with pytest.raises(TypeError):
        RS.issue(_outcome(), doc, raw, ("e",))          # firma antigua sin credencial


def test_manifest_sha_is_actual_file_bytes_not_reconstructed(tmp_path, monkeypatch):
    manifest = {"snapshot_id": "S1", "window_id": "w/oos"}
    monkeypatch.setattr(W.S, "validate_manifest", lambda m: m)
    raw = b'{ "window_id":"w/oos",   "snapshot_id":"S1" }\n'          # formato distinto al de json.dumps
    (tmp_path / "S1.json").write_bytes(raw)
    got = W._manifest_file_sha(manifest, tmp_path)
    assert got == RS.evaluation_hash(raw)
    rebuilt = (__import__("json").dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    assert got != RS.evaluation_hash(rebuilt)
    with pytest.raises(W.ProvenanceError):
        W._manifest_file_sha(manifest, None)                          # sin archivo accesible: no se emite
    (tmp_path / "S1.json").write_bytes(b'{"snapshot_id":"S1","window_id":"OTRO"}')
    with pytest.raises(W.ProvenanceError):
        W._manifest_file_sha(manifest, tmp_path)                      # archivo distinto del verificado
    with pytest.raises(FileNotFoundError):
        W._manifest_file_sha({"snapshot_id": "NOPE"}, tmp_path)


def test_issue_without_manifest_dir_yields_no_issued_result(monkeypatch):
    class Prov:
        consumption = '{"kind": "PARTITION_CONSUMED"}'
        grant = ("EXP-0001", "oos", "S", "DEC-1.md", "p")

    class Reg:
        def _load(self):
            return [b"l"], [{"kind": "PARTITION_CONSUMED"}]
    monkeypatch.setattr(W, "_check_evidence", lambda *a: None)
    monkeypatch.setattr(W.PR, "_preregistered_sha", lambda r, e: "a" * 64)
    data = type("D", (), {"provenance": Prov()})()
    oc = _outcome()
    out, issued = W._issue(oc, data, {"snapshot_id": "S", "window_id": "w"}, Reg(), "EXP-0001", None)
    assert out is oc and issued is None
