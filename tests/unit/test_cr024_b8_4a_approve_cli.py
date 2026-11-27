"""B8.4a (CR-023/024/025 v1.13): comando CLI `approve` genuino (sintético): aprobación, denegación y elusión."""
import argparse
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


def run(reg, c, tmp, *, confirm=True, ref=AREF, sel=None, manifest_dir=None):
    selp = tmp / "sel.json"
    selp.write_bytes(SEL if sel is None else sel)
    a = argparse.Namespace(experiment=EID, decision_ref=ref, selection_inputs=str(selp), confirm=confirm)
    return C._approve(a, registry_path=reg.path, manifest_dir=manifest_dir or c["manifest_dir"],
                      decisions_dir=reg.decisions_dir, prereg_root=c["pstore"].root)


def test_cli_approval_genuine_persists_five_field_binding(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    assert run(reg, c, tmp_path) == 0
    assert reg.state(EID) == "APPROVED"
    b = reg.records()[-1]["evidence"]["approval_binding"]
    assert X._approval_binding_ok(b) and len(b) == 5


def test_cli_denials_write_nothing(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    before = reg.path.read_bytes()
    assert run(reg, c, tmp_path, confirm=False) == 2                         # sin confirmación del propietario
    assert run(reg, c, tmp_path, ref="DEC-000_inexistente.md") == 1          # decision_ref inexistente
    assert run(reg, c, tmp_path, sel=b'{"x":1}') == 1                        # selection_inputs ≠ SHA citado
    assert run(reg, c, tmp_path, manifest_dir=tmp_path / "vacio") == 1       # manifiestos ausentes
    approval_doc(reg, store, line=False)                                     # sin línea APROBACION
    assert run(reg, c, tmp_path) == 1
    approval_doc(reg, store, edit=lambda ln: ln.replace("OOS=", "OOS=0"))    # línea que no liga el resultado
    assert run(reg, c, tmp_path) == 1
    assert reg.path.read_bytes() == before and reg.state(EID) == "HUMAN_REVIEW"


def test_cli_denies_corrupt_evidence_and_ambiguous_consumption(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    before = reg.path.read_bytes()
    p = store.path_for(EID, "oos")
    p.chmod(0o644)
    p.write_bytes(p.read_bytes() + b" ")                                     # evidencia corrupta
    assert run(reg, c, tmp_path) == 1 and reg.path.read_bytes() == before


def test_cli_has_no_binding_or_bypass_surface(tmp_path, gdev):
    for flag in ("--approval-binding", "--binding", "--no-check", "--force"):
        with pytest.raises(SystemExit):
            C.main(["approve", "--experiment", EID, "--decision-ref", AREF, "--selection-inputs", "x", flag, "{}"])
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    before = reg.path.read_bytes()
    with pytest.raises(X.ExperimentError, match="approval_check"):           # transition directa sin check
        reg.transition(EID, "APPROVED", actor="propietario", evidence={"decision_ref": AREF})
    with pytest.raises(X.ExperimentError, match="approval_binding"):         # binding del llamador
        reg.transition(EID, "APPROVED", actor="propietario", evidence={"decision_ref": AREF, "approval_binding": {}})
    assert reg.path.read_bytes() == before


def test_cli_denies_ambiguous_consumption(tmp_path, gdev, capsys):
    import json
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    rec = next(r for r in reg.records() if r["kind"] == "PARTITION_CONSUMED" and r["partition"] == "oos")
    with open(reg.path, "a") as fh:                                          # segundo consumo distinto, misma ventana
        fh.write(json.dumps({**rec, "decision_ref": "DEC-777_otra.md"}) + "\n")
    before = reg.path.read_bytes()
    assert run(reg, c, tmp_path) == 1
    assert "ERROR de aprobación" in capsys.readouterr().err and reg.path.read_bytes() == before


def test_main_integration_with_isolated_default_paths(tmp_path, gdev, monkeypatch):
    from swingpilot.research import prereg_store as PS
    reg, store, wins, c = human_review(tmp_path, gdev)
    approval_doc(reg, store)
    monkeypatch.setattr(C, "REGISTRY_PATH", reg.path)
    monkeypatch.setattr(C, "MANIFEST_DIR", c["manifest_dir"])
    monkeypatch.setattr(PS, "DEFAULT_ROOT", c["pstore"].root)
    monkeypatch.setattr(X, "REPO_DECISIONS_DIR", reg.decisions_dir)
    selp = tmp_path / "sel.json"
    selp.write_bytes(SEL)
    argv = ["approve", "--experiment", EID, "--decision-ref", AREF, "--selection-inputs", str(selp)]
    assert C.main(argv) == 2 and reg.state(EID) == "HUMAN_REVIEW"            # sin --confirm
    assert C.main(argv + ["--confirm"]) == 0 and reg.state(EID) == "APPROVED"
