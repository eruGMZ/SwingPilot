"""CR-024 v1.12 CR24-I3 (I3a–I3c): recuperación EVIDENCE_ONLY solo por CLI, consumo único por experimento y
partición entre snapshots, OOS favorable autoritativo en ET-4/ET-5/ET-6/`resolve_lockbox` y orquestación con
persistencia. E2E genuino, recuperación, bypass e inyección de fallos. Sintético; sin datos reales."""
import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_snapshot import _GENUINE, _decisions, _loader, gdev, ggrant, grant, make_genuine  # noqa: E402,F401
from test_cr023_b6_context_reading import EID, consumed  # noqa: E402
from test_cr023_b7_e2e_window import REF, ctx, frozen_statistics, ready  # noqa: E402,F401
from test_cr023_b7_acceptance_window import Logic, MODEL  # noqa: E402
from test_cr023_b7_provenance_window import _build_lockbox  # noqa: E402
from tape import favorable_tape  # noqa: E402,F401
from swingpilot.research import cli as C  # noqa: E402
from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research import partitions as P  # noqa: E402
from swingpilot.research import preregistration as PR  # noqa: E402
from swingpilot.research import result_store as RST  # noqa: E402
from swingpilot.research import window_evaluation as W  # noqa: E402


def _attest(reg):
    sha = PR._preregistered_sha(reg, EID)
    dec = reg.decisions_dir / "DEC-999_eval.md"
    dec.write_text(dec.read_text() + "AUTORIZA: EXP-0900 lockbox SNAP-0902\n"
                   f"AUTORIZA: ATESTACION {EID}/LOCKBOX SNAP-0902 SHA256={sha} "
                   "V1=CONFIRMADA V6=CONFIRMADA V7=CONFIRMADA\n")


def _issued_oos(tmp, gdev):
    res, reg, loader = ready(tmp, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    oc, issued = W.evaluate_window_issued(data, Logic(), MODEL, reg, loader.prereg_store, EID,
                                          manifest=res.manifest, **ctx(reg, loader))
    return res, reg, loader, oc, issued, RST.for_registry(reg)


def _evidence_only(tmp, gdev, monkeypatch):
    res, reg, loader, oc, issued, store = _issued_oos(tmp, gdev)
    monkeypatch.setattr(reg, "_write_lines", lambda lines: (_ for _ in ()).throw(OSError("fsync")))
    with pytest.raises(X.PersistenceUncertainError):
        reg.persist_window_result(store, issued, manifest_dir=loader.manifest_dir, actor="s")
    monkeypatch.undo()
    assert reg.window_result_state(store, EID, "oos") == "EVIDENCE_ONLY"
    return res, reg, loader, oc, issued, store


def _cli(reg, loader, confirm=True, window="OOS"):
    return C._recover(argparse.Namespace(experiment=EID, window=window, confirm=confirm), registry_path=reg.path,
                      manifest_dir=loader.manifest_dir)


# ---- I3c: orquestación genuina OOS → persistencia → relectura → LOCKBOX → persistencia ----------------------
def test_orchestration_persists_oos_before_resolving_lockbox_and_persists_lockbox(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    _attest(reg)
    store, seen = RST.for_registry(reg), []

    def resolve():
        seen.append(reg.window_result_state(store, EID, "oos"))       # OOS ya persistido y releído
        assert reg.window_result_favorable(store, EID, "oos") is True
        lres, lloader = _build_lockbox(tmp_path, reg, loader)       # ET-4 real exige OOS favorable autoritativo
        return lres.manifest, lambda: lloader.load_final(grant(part="lockbox", sid="SNAP-0902", ref=REF), "lockbox")
    out = W.evaluate_final_windows(lambda: loader.load_final(ggrant(part="oos"), "oos"), resolve, Logic(), MODEL,
                                   reg, loader.prereg_store, EID, oos_manifest=res.manifest, **ctx(reg, loader))
    assert seen == ["RESULT_VALID"] and out.lockbox_progression == "ATTEMPTED" and out.notes == []
    assert reg.window_result_state(store, EID, "lockbox") == "RESULT_VALID"
    marks = reg.window_results()
    assert [m["partition"] for m in marks] == ["oos", "lockbox"] and out.lockbox.verdict != "APPROVED"
    shapes = [set(r) for r in reg.consumed_partitions()]                  # forma de PARTITION_CONSUMED intacta
    assert all(s == {"at_utc", "kind", "snapshot_id", "partition", "experiment_id", "snapshot_last_open_time",
                     "decision_ref", "actor"} for s in shapes) and len(shapes) == 2


def test_orchestration_persistence_failure_reports_uncertainty_and_never_resolves_lockbox(tmp_path, gdev,
                                                                                          monkeypatch):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    real = reg._write_lines

    def fail_marker(lines):                                               # solo el marcador falla
        if any(X.RESULT_KIND.encode() in ln for ln in lines):
            raise OSError("disco")
        return real(lines)
    monkeypatch.setattr(reg, "_write_lines", fail_marker)
    with pytest.raises(X.PersistenceUncertainError):
        W.evaluate_final_windows(lambda: loader.load_final(ggrant(part="oos"), "oos"),
                                 lambda: pytest.fail("LOCKBOX resuelto"), Logic(), MODEL, reg, loader.prereg_store,
                                 EID, oos_manifest=res.manifest, **ctx(reg, loader))
    monkeypatch.undo()
    assert reg.window_result_state(RST.for_registry(reg), EID, "oos") == "EVIDENCE_ONLY"
    assert [r["partition"] for r in consumed(reg)] == ["oos"]             # sin reversión ni segundo consumo


def test_orchestration_evidence_write_failure_leaves_consumed_no_result(tmp_path, gdev, monkeypatch):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    monkeypatch.setattr(RST.ResultStore, "write", lambda *a, **k: (_ for _ in ()).throw(RST.ResultStoreError("x")))
    with pytest.raises(X.PersistenceUncertainError):
        W.evaluate_final_windows(lambda: loader.load_final(ggrant(part="oos"), "oos"),
                                 lambda: pytest.fail("LOCKBOX resuelto"), Logic(), MODEL, reg, loader.prereg_store,
                                 EID, oos_manifest=res.manifest, **ctx(reg, loader))
    monkeypatch.undo()
    assert reg.window_result_state(RST.for_registry(reg), EID, "oos") == "CONSUMED_NO_RESULT"


# ---- I3b: bypass del LOCKBOX sin OOS favorable autoritativo (ET-4, ET-6, resolve) ----------------------------
def test_lockbox_et4_blocked_when_oos_consumed_but_not_persisted(tmp_path, gdev):
    res, reg, loader, oc, issued, store = _issued_oos(tmp_path, gdev)
    _attest(reg)
    assert oc.verdict == W.FAVORABLE                                      # favorable en memoria: no autoritativo
    with pytest.raises(Exception, match="favorable autoritativo"):
        _build_lockbox(tmp_path, reg, loader)
    assert I.consumption_error(reg.records(), loader.manifest_dir, "SNAP-0902", "lockbox", EID,
                               results=store) is not None
    reg.persist_window_result(store, issued, manifest_dir=loader.manifest_dir, actor="s")
    assert X.authoritative_favorable(reg.records(), store, EID, "oos") is True
    _build_lockbox(tmp_path, reg, loader)                                 # ahora ET-4 procede


def test_v4pre_lockbox_denied_without_store_or_with_unfavorable_or_evidence_only(tmp_path, gdev, monkeypatch):
    res, reg, loader, oc, issued, store = _evidence_only(tmp_path, gdev, monkeypatch)
    recs = reg.records()
    for results in (None, store):                                         # sin almacén / EVIDENCE_ONLY
        with pytest.raises(I._Fail, match="favorable autoritativo"):
            I._oos_favorable(recs, results, EID)
    # marcador con veredicto no favorable (mismo hash no aplica): forzamos la comparación de favorabilidad
    assert X.authoritative_favorable(recs, store, EID, "oos") is False


def test_authoritative_reads_fail_closed_on_corrupted_evidence(tmp_path, gdev):
    res, reg, loader, oc, issued, store = _issued_oos(tmp_path, gdev)
    reg.persist_window_result(store, issued, manifest_dir=loader.manifest_dir, actor="s")
    path = store.path_for(EID, "oos")
    path.chmod(0o644)
    path.write_bytes(path.read_bytes().replace(b'"schema":1', b'"schema":2'))
    with pytest.raises(X.RegistryCorruptError):
        reg.window_result_favorable(store, EID, "oos")
    with pytest.raises(X.RegistryCorruptError):
        X.authoritative_favorable(reg.records(), store, EID, "oos")
    with pytest.raises(I._Fail, match="incoherente"):
        I._oos_favorable(reg.records(), store, EID)
    path.unlink()                                                          # marcador sin evidencia → CORRUPT
    with pytest.raises(X.RegistryCorruptError):
        reg.window_result_state(store, EID, "oos")


# ---- I3b: una sola consumición por experimento y partición entre snapshots -----------------------------------
def test_second_consumption_of_same_partition_in_another_snapshot_rejected(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    loader.load_final(ggrant(part="oos"), "oos")
    before = reg.path.read_bytes()
    chk = P.build_consumption_check(loader.manifest_dir, registry=reg, store=loader.prereg_store)
    with pytest.raises(X.ExperimentError, match="otra snapshot"):
        reg.claim_partition(snapshot_id="SNAP-0999", partition="oos", experiment_id=EID,
                            snapshot_last_open_time=0, decision_ref=REF, consumption_check=chk)
    assert reg.path.read_bytes() == before


# ---- I3a: recuperación EVIDENCE_ONLY solo por CLI explícito --------------------------------------------------
def test_normal_persistence_rejects_evidence_only_and_cli_recovers(tmp_path, gdev, monkeypatch):
    res, reg, loader, oc, issued, store = _evidence_only(tmp_path, gdev, monkeypatch)
    before = reg.path.read_bytes()
    with pytest.raises(X.ExperimentError, match="EVIDENCE_ONLY"):
        reg.persist_window_result(store, issued, manifest_dir=loader.manifest_dir, actor="s")
    assert _cli(reg, loader, confirm=False) == 2 and reg.path.read_bytes() == before
    assert reg.window_result_state(store, EID, "oos") == "EVIDENCE_ONLY"   # ningún acceso lo dispara
    assert _cli(reg, loader) == 0
    assert reg.window_result_state(store, EID, "oos") == "RESULT_VALID"
    m = reg.window_results()[0]
    assert m["evaluation_hash"] == issued.evaluation_hash and m["actor"] == "propietario"
    assert _cli(reg, loader) == 1                                                  # ya RESULT_VALID: no reescribe
    assert len(reg.window_results()) == 1


def test_cli_recovery_refuses_consumed_no_result_and_not_consumed(tmp_path, gdev):
    res, reg, loader, oc, issued, store = _issued_oos(tmp_path, gdev)
    before = reg.path.read_bytes()
    assert _cli(reg, loader) == 1 and _cli(reg, loader, window="LOCKBOX") == 1            # sin reconstrucción desde datos
    assert reg.path.read_bytes() == before


def test_cli_recovery_durability_failure_is_uncertain_and_writes_nothing(tmp_path, gdev, monkeypatch):
    res, reg, loader, oc, issued, store = _evidence_only(tmp_path, gdev, monkeypatch)
    before = reg.path.read_bytes()
    monkeypatch.setattr(RST.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("fsync")))
    with pytest.raises(X.PersistenceUncertainError):
        reg.recover_evidence_only(store, EID, "oos", actor="propietario", manifest_dir=loader.manifest_dir)
    assert _cli(reg, loader) == 1
    monkeypatch.undo()
    assert reg.path.read_bytes() == before
    assert reg.window_result_state(store, EID, "oos") == "EVIDENCE_ONLY"


def test_cli_recovery_rejects_evidence_rebound_to_other_consumption(tmp_path, gdev, monkeypatch):
    res, reg, loader, oc, issued, store = _evidence_only(tmp_path, gdev, monkeypatch)
    path = store.path_for(EID, "oos")
    path.chmod(0o644)
    path.write_bytes(path.read_bytes().replace(REF.encode(), b"DEC-000"))
    before = reg.path.read_bytes()
    with pytest.raises(X.ExperimentError):
        reg.recover_evidence_only(store, EID, "oos", actor="propietario", manifest_dir=loader.manifest_dir)
    assert _cli(reg, loader) == 1 and reg.path.read_bytes() == before


def test_cli_recovery_rejects_tampered_manifest_file_bytes(tmp_path, gdev, monkeypatch):
    res, reg, loader, oc, issued, store = _evidence_only(tmp_path, gdev, monkeypatch)
    mp = loader.manifest_dir / f"{res.manifest['snapshot_id']}.json"
    mp.write_bytes(mp.read_bytes() + b"\n")                  # mismos datos, bytes distintos
    before = reg.path.read_bytes()
    assert _cli(reg, loader) == 1 and reg.path.read_bytes() == before
    assert reg.window_result_state(store, EID, "oos") == "EVIDENCE_ONLY"
