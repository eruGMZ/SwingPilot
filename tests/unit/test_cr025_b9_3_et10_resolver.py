"""B9.3 (CR-025 v1.13): resolutor ET-10 genuino (sintético): una instantánea bajo _locked_et10, multi-experimento,
plazo, manipulación y entradas ausentes → UNDETERMINABLE. Sin cableado del Strategy Engine."""
import argparse
import fcntl
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from test_snapshot import _GENUINE, GSID, gdev, ggrant, grant, make_genuine  # noqa: E402,F401
from test_cr023_b6_context_reading import EID  # noqa: E402
from test_cr023_b7_e2e_window import REF, SEL, ctx, frozen_statistics, ready  # noqa: E402,F401
from test_cr024_b8_2_approval_transition import AREF, approval_doc, human_review  # noqa: E402,F401
from tape import favorable_tape  # noqa: E402,F401
from swingpilot.research import cli as C  # noqa: E402
from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research import operational_eligibility as O  # noqa: E402


def approved(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    selp = tmp_path / "sel.json"
    selp.write_bytes(SEL)
    a = argparse.Namespace(experiment=EID, decision_ref=AREF, selection_inputs=str(selp), confirm=True)
    assert C._approve(a, registry_path=reg.path, manifest_dir=c["manifest_dir"], decisions_dir=reg.decisions_dir,
                      prereg_root=c["pstore"].root) == 0
    prov = O.EvidenceProvider(reg, c["pstore"], c["manifest_dir"], {EID: selp})
    return reg, store, c, selp, prov


def test_genuine_approved_is_eligible_with_single_lock(tmp_path, gdev, monkeypatch):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    calls = []
    real = X.ExperimentRegistry._locked_et10
    monkeypatch.setattr(X.ExperimentRegistry, "_locked_et10", lambda self: (calls.append(1), real(self))[1])
    r = O.resolve_et10(prov, [EID])
    assert r[EID]["result"] == "ELIGIBLE", r
    assert len(calls) == 1                                             # una vez por ciclo
    before = reg.path.read_bytes()
    assert O.resolve_et10(prov, [EID])[EID]["result"] == "ELIGIBLE"    # sin caché: recalcula
    assert len(calls) == 2 and reg.path.read_bytes() == before         # solo lectura


def test_multi_experiment_mixed_is_per_reference(tmp_path, gdev):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    prov2 = O.EvidenceProvider(reg, c["pstore"], c["manifest_dir"], {EID: selp, "EXP-9999": selp})
    r = O.resolve_et10(prov2, [EID, "EXP-9999", "EXP-0000"])
    assert r[EID]["result"] == "ELIGIBLE"
    assert r["EXP-9999"]["result"] == "UNDETERMINABLE" and r["EXP-9999"]["nature"] == "TECHNICAL"
    assert r["EXP-0000"]["result"] == "UNDETERMINABLE" and "selection_inputs" in r["EXP-0000"]["causes"]["ET-10"]


def test_duplicate_reference_is_undeterminable(tmp_path, gdev):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    assert O.resolve_et10(prov, [EID, EID])[EID]["result"] == "UNDETERMINABLE"


def test_lock_timeout_makes_all_undeterminable(tmp_path, gdev, monkeypatch):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    monkeypatch.setattr(X, "ET10_LOCK_TIMEOUT_S", 0.05)
    lk = open(reg.path.with_name(reg.path.name + ".lock"), "a")
    fcntl.flock(lk, fcntl.LOCK_EX)
    try:
        r = O.resolve_et10(prov, [EID, "EXP-9999"])
    finally:
        lk.close()
    assert {v["result"] for v in r.values()} == {"UNDETERMINABLE"}
    assert all("RegistryLockTimeout" in v["causes"]["ET-10"] for v in r.values())
    assert O.resolve_et10(prov, [EID])[EID]["result"] == "ELIGIBLE"    # liberado: se recupera en el ciclo siguiente


def test_no_nested_lock_inside_resolution(tmp_path, gdev, monkeypatch):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    def boom(self):
        raise AssertionError("bloqueo anidado de escritor durante ET-10")
    monkeypatch.setattr(X.ExperimentRegistry, "_locked", boom)
    assert O.resolve_et10(prov, [EID])[EID]["result"] == "ELIGIBLE"


def test_tampered_result_evidence_is_undeterminable(tmp_path, gdev):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    p = store.path_for(EID, "oos")
    p.chmod(0o644)
    p.write_bytes(p.read_bytes() + b" ")
    r = O.resolve_et10(prov, [EID])[EID]
    assert r["result"] == "UNDETERMINABLE" and r["nature"] == "TECHNICAL"


def test_tampered_selection_inputs_is_undeterminable(tmp_path, gdev):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    selp.write_bytes(b'{"x":1}')
    assert O.resolve_et10(prov, [EID])[EID]["result"] == "UNDETERMINABLE"


def test_missing_inputs_are_undeterminable(tmp_path, gdev):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    for bad in (O.EvidenceProvider(reg, c["pstore"], c["manifest_dir"], {EID: tmp_path / "nada.json"}),
                O.EvidenceProvider(reg, c["pstore"], tmp_path / "vacio", {EID: selp}),
                O.EvidenceProvider(reg, c["pstore"], c["manifest_dir"], {})):
        assert O.resolve_et10(bad, [EID])[EID]["result"] == "UNDETERMINABLE"


def test_ambiguous_consumption_is_undeterminable(tmp_path, gdev):
    import json
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    rec = next(r for r in reg.records() if r["kind"] == "PARTITION_CONSUMED" and r["partition"] == "oos")
    with open(reg.path, "a") as fh:
        fh.write(json.dumps({**rec, "decision_ref": "DEC-777_otra.md"}) + "\n")
    assert O.resolve_et10(prov, [EID])[EID]["result"] == "UNDETERMINABLE"


def test_edited_approval_line_is_technical_v9(tmp_path, gdev):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    approval_doc(reg, store, line=False)                                # V9 relee la atestación original
    r = O.resolve_et10(prov, [EID])[EID]
    assert r["result"] == "UNDETERMINABLE" and r["nature"] == "TECHNICAL"


def test_combine_preserves_method_and_tech_precedence():
    n = {"result": "NOT_ELIGIBLE", "causes": {"V8": "contaminada"}}
    e = {"result": "ELIGIBLE", "causes": {}}
    t = {"result": "UNDETERMINABLE", "causes": {"V9": "x"}}
    assert O._combine([e, e])["result"] == "ELIGIBLE"
    m = O._combine([e, n])
    assert m["result"] == "NOT_ELIGIBLE" and m["nature"] == "METHODOLOGICAL" and m["causes"] == {"V8": "contaminada"}
    assert O._combine([n, t])["result"] == "UNDETERMINABLE"            # la causa técnica prevalece
    assert O._combine([])["result"] == "UNDETERMINABLE"
    assert O._combine([{"result": "ELIGIBLE?", "causes": {}}])["result"] == "UNDETERMINABLE"


def test_v9_in_et10_blocks_non_approved(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)                  # HUMAN_REVIEW: V9 exige APPROVED
    selp = tmp_path / "sel.json"
    selp.write_bytes(SEL)
    prov = O.EvidenceProvider(reg, c["pstore"], c["manifest_dir"], {EID: selp})
    assert O.resolve_et10(prov, [EID])[EID]["result"] == "UNDETERMINABLE"


def test_causes_are_specific_not_generic_context_failure(tmp_path, gdev):
    reg, store, c, selp, prov = approved(tmp_path, gdev)
    selp.write_bytes(b'{"x":1}')
    assert "selection_inputs" in O.resolve_et10(prov, [EID])[EID]["causes"]["ET-10"]
    selp.write_bytes(SEL)
    approval_doc(reg, store, line=False)
    causes = O.resolve_et10(prov, [EID])[EID]["causes"]
    assert any("V9" in w for w in causes.values()), causes
