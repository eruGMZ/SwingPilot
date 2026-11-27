"""CR-024 v1.12 CR24-I2c — persistencia coordinada y conciliación B.6: E2E genuino (evaluate_window_issued →
persistencia) e inyección de fallos. Sintético; sin LOCKBOX."""
import copy
import os
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


# --- FIX-D (QA-C2-01 / sonda P4): una única evaluación confirmatoria por consumo autorizado -----------

class _CountingLogic(Logic):
    calls = 0

    def entry_signal(self, b, i):
        type(self).calls += 1
        return super().entry_signal(b, i)


def _evaluate(res, reg, loader, data, logic):
    return W.evaluate_window_issued(data, logic, MODEL, reg, loader.prereg_store, EID,
                                    manifest=res.manifest, **ctx(reg, loader))


def test_fixd_second_evaluation_of_same_consumption_denied_before_strategy_logic(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    _CountingLogic.calls = 0
    _evaluate(res, reg, loader, data, _CountingLogic())
    first = _CountingLogic.calls
    assert first > 0
    for logic in (_CountingLogic(), Logic()):                          # misma lógica y lógica alternativa (P4)
        with pytest.raises(W.EvaluationAlreadyStarted):
            _evaluate(res, reg, loader, data, logic)
    assert _CountingLogic.calls == first                               # la lógica nunca se ejecutó de nuevo


def test_fixd_denial_does_not_depend_on_data_object_identity_or_mutation(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    _evaluate(res, reg, loader, data, Logic())
    import dataclasses
    clone = dataclasses.replace(data, data=data.data.copy())            # otro objeto, misma procedencia/consumo
    _CountingLogic.calls = 0
    with pytest.raises(W.EvaluationAlreadyStarted):
        _evaluate(res, reg, loader, clone, _CountingLogic())
    assert _CountingLogic.calls == 0


def test_fixd_concurrent_evaluations_run_strategy_logic_once(tmp_path, gdev):
    import threading
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    _CountingLogic.calls = 0
    out, barrier = [], threading.Barrier(4)

    def worker():
        barrier.wait()
        try:
            _evaluate(res, reg, loader, data, _CountingLogic())
            out.append("ok")
        except W.EvaluationAlreadyStarted:
            out.append("denied")
    ts = [threading.Thread(target=worker) for _ in range(4)]
    [t.start() for t in ts]
    [t.join(60) for t in ts]
    assert sorted(out) == ["denied", "denied", "denied", "ok"]
    assert _CountingLogic.calls > 0


def test_fixd_failure_path_keeps_the_claim_no_retry_and_persistence_unchanged(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")

    class Boom(Logic):
        def entry_signal(self, b, i):
            raise RuntimeError("fallo del motor")
    oc, issued = _evaluate(res, reg, loader, data, Boom())              # fallo técnico emitido, no se propaga
    assert oc.verdict == "INCONCLUSIVE" and oc.nature == "TECHNICAL" and oc.retry_allowed is False
    n = reg.path.read_bytes()
    with pytest.raises(W.EvaluationAlreadyStarted):                     # sin reevaluación tras fallo
        _evaluate(res, reg, loader, data, Logic())
    assert reg.path.read_bytes() == n
    store = RST.ResultStore(tmp_path / "results")
    reg.persist_window_result(store, issued, manifest_dir=loader.manifest_dir, actor="orquestador")   # persistencia original
    assert reg.window_result_state(store, EID, "oos") == "RESULT_VALID"


def test_fixd_persisted_result_denies_evaluation_after_restart(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    _, issued = _evaluate(res, reg, loader, data, Logic())
    reg.persist_window_result(RST.ResultStore(tmp_path / "results"), issued, manifest_dir=loader.manifest_dir,
                              actor="orquestador")
    _CountingLogic.calls = 0
    with pytest.raises(W.EvaluationAlreadyStarted):
        _evaluate(res, reg, loader, data, _CountingLogic())
    assert _CountingLogic.calls == 0


_CHILD = """
import sys
sys.path.insert(0, {src!r})
from pathlib import Path
from swingpilot.research import window_evaluation as W
class R:
    path = Path({reg!r})
    def _load(self): return [], []
    def window_results(self, records): return []
class Prov: consumption = {rec!r}
class D: partition = "oos"; provenance = Prov()
try:
    W._claim_single_evaluation(D(), R(), "EXP-0900"); print("WON")
except W.EvaluationAlreadyStarted:
    print("DENIED")
"""


def _spawn(reg_path, rec):
    import subprocess
    src = str(Path(__file__).resolve().parents[2] / "src")
    return subprocess.Popen([sys.executable, "-I", "-c", _CHILD.format(src=src, reg=str(reg_path), rec=rec)],
                            stdout=subprocess.PIPE, text=True)


def test_fixd_claim_is_exclusive_across_separate_processes(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    rec = data.provenance.consumption
    procs = [_spawn(reg.path, rec) for _ in range(4)]                   # reclamos concurrentes de la misma clave
    outs = sorted(p.communicate(timeout=120)[0].strip() for p in procs)
    assert outs == ["DENIED", "DENIED", "DENIED", "WON"]
    _CountingLogic.calls = 0                                            # el proceso padre también queda denegado
    with pytest.raises(W.EvaluationAlreadyStarted):
        _evaluate(res, reg, loader, data, _CountingLogic())
    assert _CountingLogic.calls == 0


def test_fixd_restart_before_persistence_cannot_produce_an_alternative_result(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    _evaluate(res, reg, loader, data, Logic())                          # evalúa; el proceso «muere» sin persistir
    n = reg.path.read_bytes()
    reg2 = X.ExperimentRegistry(reg.path, reg.decisions_dir)            # reinicio: estado nuevo en memoria
    assert reg2.window_result_state(RST.ResultStore(tmp_path / "results"), EID, "oos") == "CONSUMED_NO_RESULT"
    _CountingLogic.calls = 0
    with pytest.raises(W.EvaluationAlreadyStarted):
        W.evaluate_window_issued(data, _CountingLogic(), MODEL, reg2, loader.prereg_store, EID,
                                 manifest=res.manifest, **ctx(reg2, loader))
    assert _CountingLogic.calls == 0 and reg.path.read_bytes() == n     # sin reevaluación ni cambios


def test_fixd_claim_failure_denies_evaluation_and_never_releases(tmp_path, gdev, monkeypatch):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    real_fsync = os.fsync

    def bad(fd):
        raise OSError(5, "EIO simulado")
    monkeypatch.setattr(W.os, "fsync", bad)
    _CountingLogic.calls = 0
    with pytest.raises(W.EvaluationAlreadyStarted, match="reserva|reservar"):
        _evaluate(res, reg, loader, data, _CountingLogic())
    monkeypatch.setattr(W.os, "fsync", real_fsync)
    claims = list((reg.path.parent / (reg.path.name + ".claims")).glob("*.claim"))
    assert len(claims) == 1                                             # no se borra: no hay reintento
    with pytest.raises(W.EvaluationAlreadyStarted):
        _evaluate(res, reg, loader, data, _CountingLogic())
    assert _CountingLogic.calls == 0


@pytest.mark.parametrize("target", ["file", "claim_dir", "parent_dir"])
def test_fixfinal_d1_claim_fsync_covers_file_directory_and_parent_and_fails_closed(tmp_path, gdev, monkeypatch, target):
    """D-1: la creación inicial del directorio de reservas es duradera (fsync del padre); un fallo del fsync
    del archivo, del directorio o del padre niega la evaluación sin ejecutar la lógica y conserva la reserva."""
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    claims_dir = reg.path.parent / (reg.path.name + ".claims")
    real_fsync, seen = os.fsync, []

    def classify(fd):
        p = Path(os.readlink(f"/proc/self/fd/{fd}"))
        if p == claims_dir:
            return "claim_dir"
        if p == claims_dir.parent:
            return "parent_dir"
        return "file" if p.parent == claims_dir else None

    def spy(fd):
        kind = classify(fd)
        seen.append(kind)
        if kind == target:
            raise OSError(5, "EIO simulado")
        return real_fsync(fd)
    monkeypatch.setattr(W.os, "fsync", spy)
    _CountingLogic.calls = 0
    with pytest.raises(W.EvaluationAlreadyStarted, match="sin confirmar"):
        _evaluate(res, reg, loader, data, _CountingLogic())
    assert _CountingLogic.calls == 0 and target in seen
    assert len(list(claims_dir.glob("*.claim"))) == 1                   # la reserva se conserva
    monkeypatch.setattr(W.os, "fsync", real_fsync)
    with pytest.raises(W.EvaluationAlreadyStarted):
        _evaluate(res, reg, loader, data, _CountingLogic())
    assert _CountingLogic.calls == 0


def test_fixfinal_d1_successful_claim_fsyncs_file_directory_and_parent(tmp_path, gdev, monkeypatch):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    claims_dir = reg.path.parent / (reg.path.name + ".claims")
    real_fsync, seen = os.fsync, []

    def spy(fd):
        p = Path(os.readlink(f"/proc/self/fd/{fd}"))
        seen.append("claim_dir" if p == claims_dir else "parent_dir" if p == claims_dir.parent
                    else "file" if p.parent == claims_dir else None)
        return real_fsync(fd)
    monkeypatch.setattr(W.os, "fsync", spy)
    _evaluate(res, reg, loader, data, Logic())
    assert {"file", "claim_dir", "parent_dir"} <= set(seen)
