"""CR-023 B6.5b: `load_final` entrega context + partición bajo la misma autorización y el mismo consumo
(§C.9.4). Reutiliza las fixtures genuinas de B6.5a (`gdev`, `make_genuine`). El bloqueo de producción
sigue activo: estas pruebas lo desactivan solo mediante la fixture histórica importada."""
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_snapshot as T  # noqa: E402
from test_snapshot import (_advance_to_oos, _decisions, _GENUINE,  # noqa: E402,F401
                           _loader, _mode, _no_read, gdev, ggrant, GSID, make_genuine)
from test_cr023_b3_preregistration import EVIDENCE_REF  # noqa: E402
from swingpilot.research import partitions as P  # noqa: E402
from swingpilot.research import preregistration as PR  # noqa: E402
from swingpilot.research.experiments import (_CONSUMPTION_CHECK_KEY, ConsumptionCheck, ExperimentError,  # noqa: E402
                                              ExperimentRegistry)
from swingpilot.research.partitions import FinalEvaluationData, PartitionAccessError  # noqa: E402

EID = "EXP-0900"
PARTS = ["oos", "lockbox"]


def ready(tmp, gdev, part):
    res = make_genuine(tmp, gdev, part)
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    return res, reg, _loader(res, tmp, reg)


def consumed(reg):
    return [r for r in reg.consumed_partitions() if r["snapshot_id"] == GSID]


def contaminate(reg, part):
    _GENUINE[str(reg.path)].record_independence_deviation(
        [f"{EID}/{part.upper()}"], "UNAUTHORIZED_EXPOSURE", [EVIDENCE_REF], "UNKNOWN", "x",
        registry=reg, informed_by=[])


def assert_untouched(res, part, reg, before, reads, loader, n_log):
    assert reads == [] and consumed(reg) == [] and reg.path.read_bytes() == before
    hist = loader.access_history()
    assert len(hist) == n_log and all(r["allowed"] is False for r in hist)
    assert _mode(res.data_dir / f"{part}.parquet") == 0 and _mode(res.data_dir / "context.parquet") == 0


@pytest.mark.parametrize("part", PARTS)
def test_one_authorization_one_consumption_reads_context_then_partition(tmp_path, gdev, part, monkeypatch):
    res, reg, loader = ready(tmp_path, gdev, part)
    reads, claims = [], []
    real_read, real_claim = loader._read, reg.claim_partition
    monkeypatch.setattr(loader, "_read", lambda p: reads.append(p) or real_read(p))
    monkeypatch.setattr(reg, "claim_partition", lambda **k: claims.append(k["partition"]) or real_claim(**k))
    out = loader.load_final(ggrant(part=part), part)
    assert isinstance(out, FinalEvaluationData) and out.partition == part
    assert reads == ["context", part] and claims == [part] and len(consumed(reg)) == 1
    assert len(out) == len(out.data) == res.manifest["files"][part]["rows"]
    assert len(out.context) == res.manifest["files"]["context"]["rows"]
    assert out.context["open_time"].min() < out.data["open_time"].min()        # el context precede a la ventana
    assert [r["allowed"] for r in loader.access_history()] == [True]
    assert _mode(res.data_dir / f"{part}.parquet") == 0 and _mode(res.data_dir / "context.parquet") == 0
    with pytest.raises(PartitionAccessError, match="consumido"):                # sin segunda lectura del context
        loader.load_final(ggrant(part=part), part)
    assert reads == ["context", part]


@pytest.mark.parametrize("part", PARTS)
def test_concurrent_loaders_one_reads_context_and_partition_others_denied(tmp_path, gdev, part, monkeypatch):
    res, reg, _ = ready(tmp_path, gdev, part)
    reads, lock = [], threading.Lock()
    real = P.PartitionLoader._read
    monkeypatch.setattr(P.PartitionLoader, "_read", lambda self, p: (lock.acquire(), reads.append(p), lock.release(),
                                                                      real(self, p))[3])
    loaders = [_loader(res, tmp_path, ExperimentRegistry(tmp_path / "registry.jsonl", tmp_path / "decisions"))
               for _ in range(4)]
    out, bar = [], threading.Barrier(4)

    def go(ld):
        bar.wait()
        try:
            out.append(ld.load_final(ggrant(part=part), part))
        except Exception as exc:
            out.append(exc)
    ts = [threading.Thread(target=go, args=(ld,)) for ld in loaders]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sum(isinstance(o, FinalEvaluationData) for o in out) == 1
    assert all(isinstance(o, PartitionAccessError) for o in out if not isinstance(o, FinalEvaluationData))
    assert sorted(reads) == sorted(["context", part]) and len(consumed(reg)) == 1


def test_publication_serialized_with_claim_and_sees_the_consumption(tmp_path, gdev, monkeypatch):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    entered, release, order, seen = threading.Event(), threading.Event(), [], []
    real_build = P.build_consumption_check

    def slow_build(*a, **k):
        real = real_build(*a, **k)

        def fn(*args):
            entered.set()
            assert release.wait(10)
            return real(*args)
        return ConsumptionCheck(_CONSUMPTION_CHECK_KEY, fn)
    monkeypatch.setattr(P, "build_consumption_check", slow_build)
    res_box = []
    a = threading.Thread(target=lambda: res_box.append(loader.load_final(ggrant(part="oos"), "oos")))
    a.start()
    assert entered.wait(10)
    b = threading.Thread(target=lambda: reg.publish_under_lock(
        lambda recs: seen.append([r["kind"] for r in recs]), lambda: order.append("publish")))
    b.start()
    b.join(0.4)
    assert b.is_alive() and order == []                      # la publicación espera al claim bajo bloqueo
    release.set()
    a.join(10)
    b.join(10)
    assert order == ["publish"] and "PARTITION_CONSUMED" in seen[0] and len(res_box) == 1


@pytest.mark.parametrize("part", PARTS)
def test_contamination_after_grant_denies_without_consumption_or_reads(tmp_path, gdev, part):
    res, reg, loader = ready(tmp_path, gdev, part)
    g = ggrant(part=part)                                    # la grant ya existe; después llega la contaminación
    contaminate(reg, part)
    before, reads = reg.path.read_bytes(), _no_read(loader)
    with pytest.raises(PartitionAccessError, match="METODOLOGICA"):
        loader.load_final(g, part)
    assert_untouched(res, part, reg, before, reads, loader, 1)


@pytest.mark.parametrize("part", PARTS)
def test_contamination_between_et5_and_claim_is_caught_by_et6_under_lock(tmp_path, gdev, part, monkeypatch):
    res, reg, loader = ready(tmp_path, gdev, part)
    g = ggrant(part=part)
    real_deny = loader._deny_reason

    def deny_then_contaminate(*a):
        why = real_deny(*a)
        contaminate(reg, part)                               # ET-5 pasó; la contaminación llega antes del claim
        return why
    monkeypatch.setattr(loader, "_deny_reason", deny_then_contaminate)
    reads = _no_read(loader)
    with pytest.raises(PartitionAccessError, match="ET-6 bajo bloqueo.*METODOLOGICA"):
        loader.load_final(g, part)
    assert reads == [] and consumed(reg) == []
    assert [r["allowed"] for r in loader.access_history()] == [False]


@pytest.mark.parametrize("part", PARTS)
def test_release_denies_at_et5_and_at_et6(tmp_path, gdev, part, monkeypatch):
    res, reg, loader = ready(tmp_path, gdev, part)
    sha = PR._preregistered_sha(reg, EID)
    (tmp_path / "decisions" / "DEC-902_liberacion.md").write_text(
        f"AUTORIZA: LIBERACION {EID}/{part.upper()} SHA256={sha}\n")
    before, reads = reg.path.read_bytes(), _no_read(loader)
    with pytest.raises(PartitionAccessError, match="METODOLOGICA.*liberada"):
        loader.load_final(ggrant(part=part), part)
    monkeypatch.setattr(loader, "_deny_reason", lambda *a: None)             # ET-5 eludida: ET-6 lo detiene
    with pytest.raises(PartitionAccessError, match="ET-6 bajo bloqueo.*liberada"):
        loader.load_final(ggrant(part=part), part)
    assert_untouched(res, part, reg, before, reads, loader, 2)


@pytest.mark.parametrize("part", PARTS)
def test_direct_api_bypass_is_rejected_without_consumption_or_reads(tmp_path, gdev, part):
    res, reg, loader = ready(tmp_path, gdev, part)
    before, reads = reg.path.read_bytes(), _no_read(loader)
    kw = dict(snapshot_id=GSID, partition=part, experiment_id=EID,
              snapshot_last_open_time=res.manifest["range"]["last_open_time_ms"], decision_ref="DEC-999_eval.md")
    with pytest.raises(ExperimentError, match="consumption_check"):
        reg.claim_partition(**kw)                                           # sin credencial
    with pytest.raises(ExperimentError, match="consumption_check"):
        reg.claim_partition(**kw, consumption_check=lambda *a: None)        # invocable arbitrario
    with pytest.raises(ExperimentError, match="ligad|credencial|manifiesto"):
        reg.claim_partition(**kw, consumption_check=P.build_consumption_check(loader.manifest_dir))
    other = "lockbox" if part == "oos" else "oos"                           # credencial de otra partición
    with pytest.raises(ExperimentError, match="ligad"):
        reg.claim_partition(**kw, consumption_check=P.build_consumption_check(
            loader.manifest_dir, registry=reg, store=loader.prereg_store, decisions_dir=reg.decisions_dir,
            grant=ggrant(part=other), manifest=loader.manifest))
    with pytest.raises(PartitionAccessError):                               # context nunca se pide por sí solo
        loader.load_final(ggrant(part="context"), "context")
    with pytest.raises(PartitionAccessError):
        loader.load_train_val_for_configuration(EID, "A")                   # cargador de desarrollo
    with pytest.raises(PartitionAccessError):
        loader.load_final(None, part)
    assert reads == [] and consumed(reg) == [] and reg.path.read_bytes() == before
    assert _mode(res.data_dir / "context.parquet") == 0 and _mode(res.data_dir / f"{part}.parquet") == 0


def test_manifest_without_context_is_denied_before_consumption(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    loader.manifest = {**loader.manifest, "files": {k: v for k, v in loader.manifest["files"].items()
                                                    if k != "context"}}
    before, reads = reg.path.read_bytes(), _no_read(loader)
    with pytest.raises(PartitionAccessError, match="context"):
        loader.load_final(ggrant(part="oos"), "oos")
    assert_untouched(res, "oos", reg, before, reads, loader, 1)


@pytest.mark.parametrize("fail", ["context", "oos"])
def test_read_failure_after_consumption_delivers_nothing_and_stays_consumed(tmp_path, gdev, fail):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    real = loader._read

    def flaky(p):
        if p == fail:
            raise PartitionAccessError(f"{p}: SHA-256 no coincide con el manifiesto")
        return real(p)
    loader._read = flaky
    with pytest.raises(PartitionAccessError, match="SHA-256"):
        loader.load_final(ggrant(part="oos"), "oos")
    assert len(consumed(reg)) == 1
    assert [r["allowed"] for r in loader.access_history()] == [True, False]
    loader._read = real
    with pytest.raises(PartitionAccessError, match="consumido"):
        loader.load_final(ggrant(part="oos"), "oos")
