"""CR-024 v1.12 CR24-I2c — persistencia coordinada y conciliación B.6: E2E genuino (evaluate_window_issued →
persistencia) e inyección de fallos. Sintético; sin LOCKBOX."""
import copy
import pickle
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_snapshot import _GENUINE, _decisions, _loader, gdev, ggrant, make_genuine  # noqa: E402,F401
from test_cr023_b6_context_reading import EID  # noqa: E402,F401
from test_cr023_b7_e2e_window import REF, ctx, frozen_statistics, ready  # noqa: E402,F401
from test_cr023_b7_acceptance_window import Logic, MODEL  # noqa: E402
from tape import favorable_tape  # noqa: E402,F401
from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research import result_serialization as RS  # noqa: E402
from swingpilot.research import result_store as RST  # noqa: E402
from swingpilot.research import window_evaluation as W  # noqa: E402


def issue(tmp, gdev):
    res, reg, loader = ready(tmp, gdev, "oos")
    assert reg.window_result_state(RST.ResultStore(tmp / "results"), EID, "oos") == "NOT_CONSUMED"
    data = loader.load_final(ggrant(part="oos"), "oos")
    oc, issued = W.evaluate_window_issued(data, Logic(), MODEL, reg, loader.prereg_store, EID,
                                          manifest=res.manifest, **ctx(reg, loader))
    assert type(issued) is RS.IssuedWindowResult
    return reg, RST.ResultStore(tmp / "results"), issued, loader.manifest_dir, oc, res


def test_e2e_issue_persist_reconcile_idempotent(tmp_path, gdev):
    reg, store, issued, mdir, oc, res = issue(tmp_path, gdev)
    assert reg.window_result_state(store, EID, "oos") == "CONSUMED_NO_RESULT"
    m = reg.persist_window_result(store, issued, manifest_dir=mdir, actor="orquestador")
    assert m["kind"] == "WINDOW_RESULT_PERSISTED" and m["evaluation_hash"] == issued.evaluation_hash
    assert (store.root / EID / "oos.result.json").read_bytes() == issued.document_bytes
    assert reg.window_result_state(store, EID, "oos") == "RESULT_VALID"
    assert reg.window_result_favorable(store, EID, "oos") == (
        oc.verdict == W.FAVORABLE and oc.eligibility == "ELIGIBLE" and oc.nature is None)
    n = reg.path.read_bytes()
    assert reg.persist_window_result(store, issued, manifest_dir=mdir, actor="otro") == m
    assert reg.path.read_bytes() == n
    assert len(reg.consumed_partitions()) == 1                       # consumo intacto (forma y cardinalidad)


def test_non_genuine_results_rejected_nothing_written(tmp_path, gdev):
    reg, store, issued, mdir, *_ = issue(tmp_path, gdev)
    before = reg.path.read_bytes()
    fakes = [{"document_bytes": issued.document_bytes}, issued.document_bytes, issued.evaluation_hash, None,
             type("Fake", (), {"document_bytes": issued.document_bytes, "binding": issued.binding,
                               "evaluation_hash": issued.evaluation_hash})()]
    for f in fakes:
        with pytest.raises(X.ExperimentError):
            reg.persist_window_result(store, f, manifest_dir=mdir, actor="s")
    for op in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(Exception):
            op(issued)
    with pytest.raises(X.ExperimentError):                           # sin vía directa para el marcador
        reg._append({"kind": X.RESULT_KIND})
    assert reg.path.read_bytes() == before and not store.root.exists()
    assert not hasattr(reg, "record_window_result")


def test_manifest_bytes_are_revalidated_under_the_lock(tmp_path, gdev):
    reg, store, issued, mdir, oc, res = issue(tmp_path, gdev)
    mf = Path(mdir) / f"{res.manifest['snapshot_id']}.json"
    mf.chmod(0o644)
    mf.write_bytes(mf.read_bytes() + b"\n")                          # mismo manifiesto lógico, otros bytes
    before = reg.path.read_bytes()
    with pytest.raises(X.ExperimentError, match="manifiesto"):
        reg.persist_window_result(store, issued, manifest_dir=mdir, actor="s")
    with pytest.raises(X.ExperimentError):
        reg.persist_window_result(store, issued, manifest_dir=None, actor="s")
    assert reg.path.read_bytes() == before and not store.root.exists()


def test_consumption_binding_revalidated_registry_changed(tmp_path, gdev):
    reg, store, issued, mdir, *_ = issue(tmp_path, gdev)
    lines = reg.path.read_bytes().split(b"\n")
    raw = reg.path.read_bytes()
    reg.path.write_bytes(raw.replace(b'"actor": "propietario"', b'"actor": "propietario"  '), )  # línea distinta
    with pytest.raises((X.ExperimentError, X.RegistryCorruptError)):
        reg.persist_window_result(store, issued, manifest_dir=mdir, actor="s")
    assert not store.root.exists()


def test_failure_injection_evidence_write_fails(tmp_path, gdev, monkeypatch):
    reg, store, issued, mdir, *_ = issue(tmp_path, gdev)
    before = reg.path.read_bytes()
    monkeypatch.setattr(store, "write", lambda *a: (_ for _ in ()).throw(RST.ResultStoreWriteUncertain("x")))
    with pytest.raises(X.PersistenceUncertainError):
        reg.persist_window_result(store, issued, manifest_dir=mdir, actor="s")
    assert reg.path.read_bytes() == before
    assert reg.window_result_state(store, EID, "oos") == "CONSUMED_NO_RESULT"      # nunca éxito informado


def test_failure_injection_marker_fsync_fails_then_state_is_evidence_only(tmp_path, gdev, monkeypatch):
    reg, store, issued, mdir, *_ = issue(tmp_path, gdev)
    before = reg.path.read_bytes()
    monkeypatch.setattr(reg, "_write_lines", lambda lines: (_ for _ in ()).throw(OSError("fsync")))
    with pytest.raises(X.PersistenceUncertainError):
        reg.persist_window_result(store, issued, manifest_dir=mdir, actor="s")
    monkeypatch.undo()
    assert reg.path.read_bytes() == before
    assert reg.window_result_state(store, EID, "oos") == "EVIDENCE_ONLY"
    assert reg.path.read_bytes() == before                           # conciliar no repara
    assert reg.window_result_favorable(store, EID, "oos") is False
    # CR24-I3a (B.6): la persistencia normal NO recupera EVIDENCE_ONLY; solo el comando explícito del CLI
    with pytest.raises(X.ExperimentError, match="EVIDENCE_ONLY"):
        reg.persist_window_result(store, issued, manifest_dir=mdir, actor="s")
    assert reg.path.read_bytes() == before
    reg.recover_evidence_only(store, EID, "oos", actor="propietario", manifest_dir=mdir)
    assert reg.window_result_state(store, EID, "oos") == "RESULT_VALID"


def test_failure_injection_marker_not_visible_on_reread(tmp_path, gdev, monkeypatch):
    reg, store, issued, mdir, *_ = issue(tmp_path, gdev)
    monkeypatch.setattr(reg, "_write_lines", lambda lines: None)     # «éxito» sin escribir
    with pytest.raises(X.PersistenceUncertainError):
        reg.persist_window_result(store, issued, manifest_dir=mdir, actor="s")


def test_preexisting_different_evidence_is_conflict_not_replaced(tmp_path, gdev):
    reg, store, issued, mdir, *_ = issue(tmp_path, gdev)
    store.write(EID, "oos", RS.canonical_bytes({"schema": 1}))
    before = reg.path.read_bytes()
    with pytest.raises(X.RegistryCorruptError):
        reg.persist_window_result(store, issued, manifest_dir=mdir, actor="s")
    assert reg.path.read_bytes() == before
    assert (store.root / EID / "oos.result.json").read_bytes() == RS.canonical_bytes({"schema": 1})
    with pytest.raises(X.RegistryCorruptError):                      # evidencia no ligada al consumo
        reg.window_result_state(store, EID, "oos")
