"""CR-025 I1: `approval_binding` persistida por transition() en la evidencia de APPROVED (sintético)."""
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr024_b8_2_approval_transition import (AREF, EID, PR, X, approval_doc, approve, check_for,  # noqa: E402,F401
                                                 gdev, human_review, ggrant, grant, make_genuine, ready,
                                                 frozen_statistics, favorable_tape, ctx, _GENUINE, GSID)
from swingpilot.research import independence as I
from swingpilot.research import result_store as RST  # noqa: E402


def _setup(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    return reg, store, wins, c


def _approved(reg):
    return [r for r in reg.records() if r.get("kind") == "TRANSITION" and r.get("to") == "APPROVED"]


def test_genuine_approval_persists_exact_binding_derived_from_evidence(tmp_path, gdev):
    reg, store, wins, c = _setup(tmp_path, gdev)
    approve(reg, check_for(reg, store, wins, c))
    (rec,) = _approved(reg)
    h = {m["partition"]: m["evaluation_hash"] for m in reg.window_results()}
    line = next(l for l in (reg.decisions_dir / AREF).read_text().split("\n") if l.startswith("AUTORIZA: APROBACION"))
    assert rec["evidence"]["approval_binding"] == {
        "schema": 1, "prereg_sha256": PR._preregistered_sha(reg, EID), "oos_evaluation_hash": h["oos"],
        "lockbox_evaluation_hash": h["lockbox"],
        "attestation_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest()}
    assert rec["evidence"]["decision_ref"] == AREF


def test_caller_supplied_binding_rejected_and_nothing_written(tmp_path, gdev):
    reg, store, wins, c = _setup(tmp_path, gdev)
    n = len(reg.records())
    with pytest.raises(X.ExperimentError, match="approval_binding"):
        reg.transition(EID, "APPROVED", actor="propietario", approval_check=check_for(reg, store, wins, c),
                       evidence={"decision_ref": AREF, "approval_binding": {"schema": 1}})
    assert len(reg.records()) == n


@pytest.mark.parametrize("bad", [None, (None, None), (None, {"schema": 1}), "ok", (None, "x" * 64),
                                 (None, {"schema": True, "prereg_sha256": "a" * 64, "oos_evaluation_hash": "b" * 64,
                                         "lockbox_evaluation_hash": "c" * 64, "attestation_sha256": "d" * 64}),
                                 (None, {"schema": 1, "prereg_sha256": "A" * 64, "oos_evaluation_hash": "b" * 64,
                                         "lockbox_evaluation_hash": "c" * 64, "attestation_sha256": "d" * 64}),
                                 (None, {"schema": 1, "prereg_sha256": "a" * 64, "oos_evaluation_hash": "b" * 64,
                                         "lockbox_evaluation_hash": "b" * 64, "attestation_sha256": "d" * 64}),
                                 (None, {"schema": 1, "prereg_sha256": "a" * 64, "oos_evaluation_hash": "b" * 64,
                                         "lockbox_evaluation_hash": "c" * 64, "attestation_sha256": "d" * 64,
                                         "x": 1})])
def test_missing_or_malformed_binding_from_check_rejected(tmp_path, gdev, bad):
    reg, store, wins, c = _setup(tmp_path, gdev)
    real = check_for(reg, store, wins, c)
    n = len(reg.records())
    fake = X.ApprovalCheck(X._APPROVAL_CHECK_KEY, lambda *a: bad, reg)
    with pytest.raises(X.ExperimentError):
        approve(reg, fake)
    assert len(reg.records()) == n and not _approved(reg)
    approve(reg, real)            # el camino genuino sigue funcionando
    assert len(_approved(reg)) == 1


def test_bypass_arbitrary_callable_and_denied_et8_still_denied(tmp_path, gdev):
    reg, store, wins, c = _setup(tmp_path, gdev)
    for chk in (None, lambda *a: (None, {"schema": 1}), object()):
        with pytest.raises(X.ExperimentError):
            approve(reg, chk)
    approval_doc(reg, store, edit=lambda ln: ln + " EXTRA")        # línea alterada → ET-8 TECH
    with pytest.raises(X.ExperimentError):
        approve(reg, check_for(reg, store, wins, c))
    assert not _approved(reg)


def test_shared_verifier_returns_hash_and_rejects_wrong_prereg_or_citation(tmp_path, gdev):
    reg, store, wins, c = _setup(tmp_path, gdev)
    lines, recs = reg._load()
    sha = PR._preregistered_sha(reg, EID)
    rs = RST.for_registry(reg)
    h, cons = I.verify_result_evidence(recs, rs, EID, "oos", prereg_sha=sha, lines=lines)
    assert len(h) == 64 and cons["kind"] == "PARTITION_CONSUMED"
    with pytest.raises(I._Fail):
        I.verify_result_evidence(recs, rs, EID, "oos", prereg_sha="0" * 64, lines=lines)
    with pytest.raises(I._Fail):
        I.verify_result_evidence(recs, rs, EID, "oos", prereg_sha=sha, cited_hash="0" * 64, lines=lines)
