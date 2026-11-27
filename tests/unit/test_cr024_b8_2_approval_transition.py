"""B8.2 (CR-023 decisión 5, CR-024 B.8): HUMAN_REVIEW → APPROVED vinculante, ET-8 genuino (sintético)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from test_snapshot import _GENUINE, GSID, gdev, ggrant, grant, make_genuine  # noqa: E402,F401
from test_cr023_b6_context_reading import EID  # noqa: E402
from test_cr023_b7_e2e_window import REF, ctx, frozen_statistics, ready  # noqa: E402,F401
from test_cr023_b7_acceptance_window import Logic, MODEL  # noqa: E402
from test_cr023_b7_provenance_window import _build_lockbox  # noqa: E402
from test_cr024_i3_integration import _attest  # noqa: E402
from tape import favorable_tape  # noqa: E402,F401
from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research import preregistration as PR  # noqa: E402
from swingpilot.research import result_store as RST  # noqa: E402
from swingpilot.research import window_evaluation as W  # noqa: E402

AREF = "DEC-998_aprobacion.md"


def human_review(tmp, gdev):
    """OOS y LOCKBOX genuinos evaluados y persistidos; experimento en HUMAN_REVIEW. Devuelve (reg, store, wins, ctx)."""
    res, reg, loader = ready(tmp, gdev, "oos")
    _attest(reg)
    store, box = RST.for_registry(reg), {}

    def resolve():
        lres, lloader = _build_lockbox(tmp, reg, loader)
        box["l"] = lres
        return lres.manifest, lambda: lloader.load_final(grant(part="lockbox", sid="SNAP-0902", ref=REF), "lockbox")
    W.evaluate_final_windows(lambda: loader.load_final(ggrant(part="oos"), "oos"), resolve, Logic(), MODEL, reg,
                             loader.prereg_store, EID, oos_manifest=res.manifest, **ctx(reg, loader))
    assert reg.window_result_state(store, EID, "lockbox") == "RESULT_VALID"
    wins = [{"grant": ggrant(part="oos"), "manifest": res.manifest, "manifest_dir": loader.manifest_dir,
             "window_id": f"{EID}/OOS"},
            {"grant": grant(part="lockbox", sid="SNAP-0902", ref=REF), "manifest": box["l"].manifest,
             "manifest_dir": loader.manifest_dir, "window_id": f"{EID}/LOCKBOX"}]
    reg.transition(EID, "AUDIT", actor="orquestador")
    reg.transition(EID, "HUMAN_REVIEW", actor="orquestador")
    return reg, store, wins, {**ctx(reg, loader), "pstore": loader.prereg_store}


def approval_doc(reg, store, *, authoriza=True, line=True, edit=None):
    sha = PR._preregistered_sha(reg, EID)
    h = {m["partition"]: m["evaluation_hash"] for m in reg.window_results()}
    text = (f"AUTORIZA: {EID} APPROVED\n" if authoriza else "")
    if line:
        ln = (f"AUTORIZA: APROBACION {EID} SHA256={sha} OOS={h['oos']} LOCKBOX={h['lockbox']} "
              "V1=CONFIRMADA V6=CONFIRMADA V7=CONFIRMADA")
        text += (edit(ln) if edit else ln) + "\n"
    (reg.decisions_dir / AREF).write_text(text)


def check_for(reg, store, wins, c):
    return I.build_approval_check(reg, c["pstore"], wins, decisions_dir=reg.decisions_dir,
                                  preregistration=c["preregistration"], selection_inputs=c["selection_inputs"])


def approve(reg, check, ref=AREF, actor="propietario"):
    return reg.transition(EID, "APPROVED", actor=actor, evidence={"decision_ref": ref}, approval_check=check)


def test_genuine_et8_eligible_and_approval_persisted_under_lock(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    before = reg.path.read_bytes()
    marks = reg.window_results()
    rec = approve(reg, check_for(reg, store, wins, c))
    assert rec["to"] == "APPROVED" and reg.state(EID) == "APPROVED"
    assert reg.path.read_bytes().startswith(before) and reg.window_results() == marks     # solo se añade la transición
    # decision_ref de la aprobación y de las grants son vínculos distintos
    assert wins[0]["grant"].decision_ref == REF != AREF


def test_bypass_paths_denied(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    size = reg.path.stat().st_size
    ok = check_for(reg, store, wins, c)
    for bad in (None, lambda r, e, ev: None, object(), X.FreezeCheck(X._FREEZE_CHECK_KEY, lambda *a: None)):
        with pytest.raises(X.ExperimentError, match="approval_check"):
            reg.transition(EID, "APPROVED", actor="propietario", evidence={"decision_ref": AREF}, approval_check=bad)
    with pytest.raises(X.ExperimentError):                                   # credencial sin la clave privada
        X.ApprovalCheck(object(), lambda *a: None, reg)
    other = X.ExperimentRegistry(tmp_path / "otro.jsonl", reg.decisions_dir)    # credencial de otro registro
    with pytest.raises(X.ExperimentError, match="este registro"):
        other_check = I.build_approval_check(other, c["pstore"], wins, decisions_dir=reg.decisions_dir)
        reg.transition(EID, "APPROVED", actor="propietario", evidence={"decision_ref": AREF}, approval_check=other_check)
    with pytest.raises(X.ExperimentError, match="propietario"):
        approve(reg, ok, actor="orquestador")
    with pytest.raises(AttributeError):
        ok.registry = None
    assert reg.path.stat().st_size == size and reg.state(EID) == "HUMAN_REVIEW"


@pytest.mark.parametrize("name,kw", [
    ("sin AUTORIZA APPROVED", dict(authoriza=False)),
    ("sin línea APROBACION", dict(line=False)),
    ("línea mal formada", dict(edit=lambda l: l.replace("V6=CONFIRMADA", "V6=CONFIRMADO"))),
    ("preregistro distinto", dict(edit=lambda l: l.replace("SHA256=", "SHA256=" + "0" * 0).replace(l.split("SHA256=")[1][:64], "c" * 64))),
    ("hash OOS distinto", dict(edit=lambda l: l.replace(l.split("OOS=")[1][:64], "d" * 64))),
])
def test_denials_write_nothing(tmp_path, gdev, name, kw):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store, **kw)
    size = reg.path.stat().st_size
    with pytest.raises(X.ExperimentError):
        approve(reg, check_for(reg, store, wins, c))
    assert reg.path.stat().st_size == size and reg.state(EID) == "HUMAN_REVIEW"


def test_denial_when_approval_ref_is_not_the_line_document_or_duplicate(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    (reg.decisions_dir / "DEC-997_dup.md").write_text((reg.decisions_dir / AREF).read_text().split("\n")[1] + "\n")
    with pytest.raises(X.ExperimentError, match="exactamente una"):
        approve(reg, check_for(reg, store, wins, c))
    assert reg.state(EID) == "HUMAN_REVIEW"


def test_denial_on_unfavorable_or_missing_authoritative_result(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    p = store.path_for(EID, "lockbox")
    p.chmod(0o644)
    p.write_bytes(p.read_bytes() + b" ")                                       # evidencia alterada
    with pytest.raises(X.ExperimentError):
        approve(reg, check_for(reg, store, wins, c))
    assert reg.state(EID) == "HUMAN_REVIEW"


def test_denial_when_a_window_is_missing_or_grant_ref_is_swapped(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    with pytest.raises(X.ExperimentError, match="OOS y LOCKBOX"):
        approve(reg, check_for(reg, store, wins[:1], c))
    swapped = [{**wins[0], "grant": ggrant(part="oos", ref=AREF)}, wins[1]]      # la ref. de la aprobación no es la de la grant
    with pytest.raises(X.ExperimentError, match="ET-8"):
        approve(reg, check_for(reg, store, swapped, c))
    assert reg.state(EID) == "HUMAN_REVIEW"


def test_rejection_and_historical_records_unaffected(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    (reg.decisions_dir / "DEC-996_r.md").write_text(f"AUTORIZA: {EID} REJECTED\n")
    reg.transition(EID, "REJECTED", actor="propietario", evidence={"decision_ref": "DEC-996_r.md"})   # sin ET-8
    assert reg.state(EID) == "REJECTED" and len(reg.window_results()) == 2


def test_et8_accepts_byte_identical_logical_marker_duplicate_and_rejects_conflicting(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    lines = reg.path.read_bytes().split(b"\n")
    mark = [l for l in lines if X.RESULT_KIND.encode() in l and b'"lockbox"' in l][0]
    reg.path.write_bytes(reg.path.read_bytes() + mark + b"\n")                 # copia byte a byte idéntica (B.5)
    assert len(reg.window_results()) == 2
    res = I.eligibility(reg, c["pstore"], EID, "ET-8", preregistration=c["preregistration"],
                        selection_inputs=c["selection_inputs"], decisions_dir=reg.decisions_dir,
                        manifest=wins[1]["manifest"], decision_ref=REF, grant=wins[1]["grant"],
                        manifest_dir=wins[1]["manifest_dir"], window_id=wins[1]["window_id"], approval_ref=AREF)
    assert res["result"] == I.ELIGIBLE, res["causes"]
    assert approve(reg, check_for(reg, store, wins, c))["to"] == "APPROVED"


def test_conflicting_marker_duplicate_is_corrupt_and_blocks_approval(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    mark = [l for l in reg.path.read_bytes().split(b"\n") if X.RESULT_KIND.encode() in l and b'"oos"' in l][0]
    import json
    bad = {**json.loads(mark), "evaluator_version": "otra"}                    # mismo resultado lógico, bytes distintos
    reg.path.write_bytes(reg.path.read_bytes() + X._serialize(bad) + b"\n")
    with pytest.raises(X.RegistryCorruptError):
        reg.records()
    size = reg.path.stat().st_size
    with pytest.raises(X.ExperimentError):
        approve(reg, check_for(reg, store, wins, c))
    assert reg.path.stat().st_size == size
