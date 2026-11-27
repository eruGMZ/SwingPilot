"""CR-023 decisión 5 + CR-024 B.8 (B8.1): atestación APROBACION de ET-8 (sintético, sin datos reales)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research.result_serialization import canonical_bytes, evaluation_hash  # noqa: E402
from swingpilot.research.result_store import ResultStore  # noqa: E402

EID, PRE, REF = "EXP-0001", "a" * 64, "DEC-900_aprobacion.md"


def _doc(part, snap, cons_sha, verdict="ELIGIBLE_FOR_HUMAN_REVIEW", elig="ELIGIBLE"):
    return {"schema": 1, "experiment_id": EID, "partition": part, "prereg_sha256": PRE, "snapshot_id": snap,
            "window_id": f"{EID}/{part.upper()}", "manifest_sha256": "b" * 64,
            "consumption": {"decision_ref": "DEC-001.md", "consumed_line_sha256": cons_sha},
            "evaluator_version": "v-test",
            "outcome": {"partition": part, "verdict": verdict, "nature": None, "eligibility": elig,
                        "reasons": [], "metrics": None}}


@pytest.fixture
def env(tmp_path):
    reg = X.ExperimentRegistry(tmp_path / "registry.jsonl")
    store = ResultStore(tmp_path / "results")
    recs = [{"kind": "CREATED", "experiment_id": EID, "title": "t", "state": "IDEA", "actor": "x", "at_utc": "t"},
            {"kind": "TRANSITION", "experiment_id": EID, "from": "DESIGN", "to": "PREREGISTERED", "actor": "x",
             "evidence": {"preregistration_sha256": PRE}, "reason": "", "at_utc": "t"}]
    hashes = {}
    for i, part in enumerate(("oos", "lockbox"), 1):
        snap = f"SNAP-000{i}"
        c = {"kind": "PARTITION_CONSUMED", "snapshot_id": snap, "partition": part, "experiment_id": EID,
             "snapshot_last_open_time": 1, "decision_ref": "DEC-001.md", "actor": "propietario", "at_utc": "t"}
        recs.append(c)
        data = canonical_bytes(_doc(part, snap, X._line_sha(X._serialize(c))))
        store.write(EID, part, data)
        hashes[part] = evaluation_hash(data)
        recs.append({"at_utc": "t", "kind": X.RESULT_KIND, "experiment_id": EID, "partition": part,
                     "snapshot_id": snap, "evaluation_hash": hashes[part], "prereg_sha256": PRE,
                     "verdict": "ELIGIBLE_FOR_HUMAN_REVIEW", "eligibility": "ELIGIBLE", "evaluator_version": "v-test",
                     "consumed_line_sha256": X._line_sha(X._serialize(c)), "actor": "s"})
    reg.path.write_bytes(b"".join(X._serialize(r) + b"\n" for r in recs))
    ddir = tmp_path / "dec"
    ddir.mkdir()
    return reg, store, ddir, hashes


def _line(h, sha=PRE, eid=EID, tail="V1=CONFIRMADA V6=CONFIRMADA V7=CONFIRMADA"):
    return f"AUTORIZA: APROBACION {eid} SHA256={sha} OOS={h['oos']} LOCKBOX={h['lockbox']} {tail}"


def _run(env, *lines, ref=REF, doc=REF, extra=None, store=True, mutate=None):
    reg, st, ddir, h = env
    (ddir / doc).write_text("\n".join(lines) + "\n")
    for name, body in (extra or {}).items():
        (ddir / name).write_text(body)
    recs = reg.records()
    if mutate:
        recs = mutate(recs)
    ctx = {"records": recs, "lines": [X._serialize(r) for r in recs], "sha": PRE, "results": st if store else None}
    try:
        I._approval(ctx, EID, ddir, ref)
    except I._Fail as f:
        return f.nature, f.why
    return None


def test_valid_attestation_passes(env):
    assert _run(env, _line(env[3])) is None


@pytest.mark.parametrize("mut", [
    lambda h: _line(h).replace("CONFIRMADA", "CONFIRMADO", 1),
    lambda h: _line(h) + " ",                                            # espacio final
    lambda h: " " + _line(h),
    lambda h: _line(h).replace("OOS=", "oos="),
    lambda h: _line(h, tail="V1=CONFIRMADA V6=CONFIRMADA"),
    lambda h: _line(h).replace(h["oos"], h["oos"].upper()),
    lambda h: _line(h).replace("APROBACION", "APROBACIÓN"),
])
def test_grammar_is_strict(env, mut):
    r = _run(env, mut(env[3]))
    assert r and r[0] == I.TECH


def test_uniqueness_duplicate_in_same_or_other_document(env):
    h = env[3]
    assert _run(env, _line(h), _line(h))[0] == I.TECH
    assert _run(env, _line(h), extra={"DEC-901_x.md": _line(h) + "\n"})[0] == I.TECH
    assert _run(env, "sin linea")[0] == I.TECH


def test_decision_ref_binding(env):
    h = env[3]
    assert _run(env, _line(h), ref="DEC-777_otra.md")[0] == I.TECH              # documento inexistente
    r = _run(env, _line(h), ref="DEC-901_x.md", extra={"DEC-901_x.md": "nada\n"})   # línea en otro documento
    assert r and "decision_ref" in r[1]
    assert _run(env, _line(h), ref="../x.md")[0] == I.TECH


def test_prereg_hash_binding(env):
    assert _run(env, _line(env[3], sha="c" * 64))[0] == I.TECH


@pytest.mark.parametrize("part", ["oos", "lockbox"])
def test_evaluation_hash_binding(env, part):
    h = dict(env[3])
    h[part] = "d" * 64
    assert _run(env, _line(h))[0] == I.TECH


def test_unfavorable_authoritative_result_denied(env):
    reg, st, ddir, h = env
    cons = [r for r in reg.records() if r["kind"] == "PARTITION_CONSUMED" and r["partition"] == "lockbox"][0]
    data = canonical_bytes(_doc("lockbox", "SNAP-0002", X._line_sha(X._serialize(cons)), verdict="NOT_ELIGIBLE", elig="NOT_ELIGIBLE"))
    p = st.path_for(EID, "lockbox")
    p.chmod(0o644)
    p.write_bytes(data)                                                       # evidencia distinta de la del marcador
    assert _run(env, _line(h))[0] == I.TECH                                   # hash / repetición de campos ya no coinciden


def test_missing_result_store_or_marker_or_tampered_evidence(env):
    reg, st, ddir, h = env
    assert _run(env, _line(h), store=False)[0] == I.TECH
    p = st.path_for(EID, "oos")
    p.chmod(0o644)
    p.write_bytes(b"{}")
    assert _run(env, _line(h))[0] == I.TECH


def test_v4post_requires_owner_actor(env):
    other = lambda recs: [{**r, "actor": "otro"} if r["kind"] == "PARTITION_CONSUMED" else r for r in recs]
    r = _run(env, _line(env[3]), mutate=other)
    assert r and r[0] == I.TECH and "V4-post" in r[1]
    dup = lambda recs: recs + [r for r in recs if r["kind"] == "PARTITION_CONSUMED"][:1]
    assert "V4-post" in _run(env, _line(env[3]), mutate=dup)[1] or _run(env, _line(env[3]), mutate=dup)[0] == I.TECH


def test_et8_wiring_is_technical_without_context_and_has_approval_check(env):
    reg, st, ddir, h = env
    assert "V1b" in I.STAGES["ET-8"]                                          # independencia existente conservada
    out = I.stage_checks(reg, st, EID, "ET-8", decisions_dir=ddir, approval_ref=REF)
    assert out["APROBACION"][0] == I.TECH and out["V2"][0] == I.TECH          # sin preregistro verificable
    assert "APROBACION" not in I.stage_checks(reg, st, EID, "ET-9", decisions_dir=ddir)


def test_consistent_but_unfavorable_result_denied(env, monkeypatch):
    monkeypatch.setattr(X, "authoritative_favorable", lambda *a: False)
    r = _run(env, _line(env[3]))
    assert r and r[0] == I.TECH and "no es favorable" in r[1]
