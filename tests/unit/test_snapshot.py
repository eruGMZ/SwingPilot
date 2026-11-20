"""FEAT-015 — TC-ML-001, TC-ML-015, TC-ML-016, TC-ML-017, TC-ML-019 y control de OOS/LOCKBOX.
Incluye las pruebas de QA3-02, 03, 04, 06, 09, 10 y 15.

Sin red: Binance simulado con un histórico corto.
"""
import json
import os
import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.market_data import BinancePublicClient, interval_ms  # noqa: E402
from swingpilot.research import snapshot as SN  # noqa: E402
from swingpilot.research.experiments import ExperimentError, ExperimentRegistry  # noqa: E402
from swingpilot.research.partitions import (FinalEvaluationGrant, PartitionAccessError,  # noqa: E402
                                            PartitionLoader)
from swingpilot.research.snapshot import (DAY_MS, SnapshotError, _date_ms, build_snapshot,  # noqa: E402
                                          check_new_lockbox, compute_cuts, load_manifest,
                                          verify_snapshot)

START = _date_ms("2017-08-17")
DAYS = 400
H = 3_600_000
SERVER = START + DAYS * DAY_MS + 5 * H + 7     # día 400, 05:00:00.007 UTC
LISTING = START + 4 * H                          # 1h y 4h empiezan a las 04:00 del primer día
MISSING = {("1h", START + 30 * DAY_MS + 3 * H), ("4h", START + 200 * DAY_MS)}
ROOT = os.geteuid() == 0


class SmallBinance:
    def __init__(self, missing=MISSING, truncate_1h_after=None, listing=LISTING):
        self.missing, self.truncate, self.listing = set(missing), truncate_1h_after, listing

    def __call__(self, url):
        u = urllib.parse.urlparse(url)
        q = dict(urllib.parse.parse_qsl(u.query))
        if u.path == "/api/v3/time":
            return {"serverTime": SERVER}
        iv = q["interval"]
        step = interval_ms(iv)
        first = START if iv == "1d" else self.listing
        t = max((int(q["startTime"]) + step - 1) // step * step, first)
        end = int(q.get("endTime", SERVER))
        rows = []
        while t <= min(end, SERVER) and len(rows) < int(q["limit"]):
            if self.truncate and iv == "1h" and len(rows) >= self.truncate:
                break   # servidor que corta la respuesta (QA3-02)
            if (iv, t) not in self.missing:
                p = 1000 + (t // step) % 50
                rows.append([t, str(p), str(p + 5), str(p - 5), str(p + 1), "3.5", t + step - 1, "0", 1, "0", "0", "0"])
            t += step
        return rows


def build(tmp, sid="SNAP-TEST", fb=None, consumed=()):
    return build_snapshot(BinancePublicClient(transport=fb or SmallBinance()), sid, tmp / "var" / "snapshots",
                          tmp / "research" / "snapshots", consumed_lockboxes=list(consumed))


@pytest.fixture
def snap(tmp_path):
    return build(tmp_path), tmp_path


def _decisions(tmp, text="EXP-T lockbox oos SNAP-TEST"):
    dec = tmp / "decisions"
    dec.mkdir(exist_ok=True)
    (dec / "DEC-999_eval.md").write_text(text)
    return dec


def _loader(res, tmp, reg=None):
    return PartitionLoader(res.manifest_path, tmp / "var" / "snapshots", tmp / "access.jsonl", registry=reg)


# --- TC-ML-015 / TC-ML-017 ---------------------------------------------------------------------

def test_tc_ml_015_three_partitions_hashes_identical_cuts_and_50_20_15_15(snap):
    res, tmp = snap
    m = res.manifest
    assert sorted(m["files"]) == ["lockbox", "oos", "train_val"]
    assert all(len(i["sha256"]) == 64 for i in m["files"].values())
    assert set(m["writer"]) == {"python", "pandas", "pyarrow"}
    cuts = m["cuts_ms"]
    assert all(v % DAY_MS == 0 for v in cuts.values())
    # Proporciones por días: Train 50, Validation 20, OOS 15, LOCKBOX 15 (± 1 día por el corte a medianoche)
    days = {"train": (cuts["train_end"] - START) // DAY_MS, "val": (cuts["val_end"] - cuts["train_end"]) // DAY_MS,
            "oos": (cuts["oos_end"] - cuts["val_end"]) // DAY_MS, "lockbox": (START + DAYS * DAY_MS - cuts["oos_end"]) // DAY_MS}
    assert days == {"train": 200, "val": 80, "oos": 60, "lockbox": 60}
    # Cortes idénticos para 1d, 4h y 1h
    for part in ("oos", "lockbox"):
        firsts = {iv: s["first_open_time_utc"] for iv, s in m["files"][part]["per_interval"].items()}
        assert len(set(firsts.values())) == 1, firsts
    assert sum(m["files"][p]["per_interval"]["1d"]["rows"] for p in m["files"]) == DAYS
    assert json.loads(res.manifest_path.read_text()) == m


def test_first_partial_day_is_declared_not_counted_as_gap(snap):
    res, _ = snap
    m = res.manifest
    assert m["listing_start"]["1h"] == {"first_open_time_utc": "2017-08-17T04:00:00.000Z",
                                        "rows_before_first_candle_excluded": 4}
    assert m["listing_start"]["4h"]["rows_before_first_candle_excluded"] == 1
    assert m["files"]["train_val"]["per_interval"]["1h"]["first_open_time_utc"] == "2017-08-17T04:00:00.000Z"
    # 1h: 400 días × 24 − 4 filas previas a la cotización
    assert sum(m["files"][p]["per_interval"]["1h"]["rows"] for p in m["files"]) == DAYS * 24 - 4


def test_tc_ml_017_gaps_are_nan_and_counted_consistently(snap):
    res, tmp = snap
    m = res.manifest
    assert m["gaps_total"] == {"1d": 0, "4h": 1, "1h": 1}
    for iv in ("1d", "4h", "1h"):   # QA3-09: el total coincide con la suma por partición
        assert m["gaps_total"][iv] == sum(m["files"][p]["per_interval"][iv]["gaps"] for p in m["files"])
    h1 = _loader(res, tmp).load_train_val("1h")
    row = h1[h1["open_time"] == START + 30 * DAY_MS + 3 * H]
    assert len(row) == 1 and row[["open", "high", "low", "close", "volume"]].isna().all(axis=None)


def test_only_closed_candles_in_snapshot(snap):
    res, _ = snap
    assert res.manifest["range"]["last_open_time_ms"] == START + (DAYS - 1) * DAY_MS


# --- QA3-02: descarga truncada o incompleta --------------------------------------------------

def test_qa3_02_truncated_download_aborts_without_sealing(tmp_path):
    with pytest.raises(SnapshotError, match="incompleta"):
        build(tmp_path, fb=SmallBinance(truncate_1h_after=300))
    assert not (tmp_path / "var" / "snapshots" / "SNAP-TEST").exists()
    assert not (tmp_path / "research" / "snapshots" / "SNAP-TEST.json").exists()


def test_qa3_02_missing_last_candle_aborts(tmp_path):
    last_1h = (SERVER // H) * H - H
    with pytest.raises(SnapshotError):
        build(tmp_path, fb=SmallBinance(missing={("1h", last_1h)}))


def test_qa3_02_interval_starting_after_first_day_aborts(tmp_path):
    with pytest.raises(SnapshotError, match="primer día"):
        build(tmp_path, fb=SmallBinance(listing=START + 2 * DAY_MS))


# --- QA3-10: cortes enteros ------------------------------------------------------------------

@pytest.mark.parametrize("ndays", [1000, 999, 1001, 3400, 3380, 3700])
def test_qa3_10_integer_cuts(ndays):
    c = compute_cuts(START, START + ndays * DAY_MS)
    assert c["train_end"] == START + (ndays * 50 // 100) * DAY_MS
    assert c["val_end"] == START + (ndays * 70 // 100) * DAY_MS
    assert c["oos_end"] == START + (ndays * 85 // 100) * DAY_MS


# --- TC-ML-015: alteración, reescritura, id, escritura atómica (QA3-15) -----------------------

def test_tc_ml_015_tampering_is_detected(snap):
    res, tmp = snap
    path = res.data_dir / "train_val.parquet"
    assert verify_snapshot(res.manifest_path, tmp / "var" / "snapshots")["train_val"]
    os.chmod(path, 0o644)
    with open(path, "ab") as fh:
        fh.write(b"x")
    with pytest.raises(SnapshotError):
        verify_snapshot(res.manifest_path, tmp / "var" / "snapshots")
    with pytest.raises(PartitionAccessError):
        _loader(res, tmp).load_train_val()


def test_snapshot_is_never_rewritten(snap):
    _, tmp = snap
    with pytest.raises(SnapshotError, match="ya existe"):
        build(tmp)


@pytest.mark.parametrize("bad", ["../escape", "SNAP-1", "snap-0001", "SNAP-0001/x", ""])
def test_qa3_15_snapshot_id_is_validated(tmp_path, bad):
    with pytest.raises(SnapshotError, match="identificador"):
        build(tmp_path, sid=bad)


def test_qa3_15_failed_write_leaves_no_orphan_and_allows_retry(tmp_path, monkeypatch):
    calls = {"n": 0}
    real = SN.pq.write_table

    def flaky(table, path, *a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disco lleno")
        return real(table, path, *a, **k)
    monkeypatch.setattr(SN.pq, "write_table", flaky)
    with pytest.raises(OSError):
        build(tmp_path)
    root = tmp_path / "var" / "snapshots"
    assert list(root.iterdir()) == []                    # ni directorio final ni temporal
    monkeypatch.setattr(SN.pq, "write_table", real)
    assert build(tmp_path).data_dir.is_dir()             # el reintento funciona


def _fail_at_manifest_commit(monkeypatch, action):
    """Hace fallar el `os.replace` del manifiesto (después del renombrado del directorio)."""
    real = SN.os.replace

    def replace(src, dst, *a, **k):
        if str(dst).endswith(".json"):
            action()
        return real(src, dst, *a, **k)
    monkeypatch.setattr(SN.os, "replace", replace)


def test_qa3r2_02_failure_between_rename_and_manifest_rolls_back(tmp_path, monkeypatch):
    def boom():
        raise OSError("fallo simulado entre renombrado y manifiesto")
    _fail_at_manifest_commit(monkeypatch, boom)
    with pytest.raises(OSError, match="fallo simulado"):
        build(tmp_path)
    root, mdir = tmp_path / "var" / "snapshots", tmp_path / "research" / "snapshots"
    assert list(root.iterdir()) == []                         # ni datos renombrados ni temporales
    assert list(mdir.iterdir()) == []                         # ni manifiesto ni manifiesto temporal
    monkeypatch.undo()
    res = build(tmp_path)                                     # el reintento funciona
    assert verify_snapshot(res.manifest_path, root)["train_val"]
    assert res.manifest["incomplete_build_quarantined"] is None


_KILL_SCRIPT = """
import os, sys
from pathlib import Path
sys.path.insert(0, {unit!r})
import test_snapshot as T
real = T.SN.os.replace
def replace(src, dst, *a, **k):
    if str(dst).endswith(".json"):
        os._exit(9)                       # muerte del proceso: no se ejecuta ningún except/finally
    return real(src, dst, *a, **k)
T.SN.os.replace = replace
T.build(Path({tmp!r}))
"""


def test_qa3r2_02_killed_process_leaves_nothing_consumable_and_retry_quarantines(tmp_path):
    import subprocess
    script = _KILL_SCRIPT.format(unit=str(Path(__file__).parent), tmp=str(tmp_path))
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 9, proc.stderr
    root, mdir = tmp_path / "var" / "snapshots", tmp_path / "research" / "snapshots"
    manifest_path = mdir / "SNAP-TEST.json"
    assert (root / "SNAP-TEST").is_dir() and not manifest_path.exists()   # estado tras la muerte
    # Sin manifiesto, la snapshot no es consumible ni verificable como completa.
    with pytest.raises(FileNotFoundError):
        verify_snapshot(manifest_path, root)
    with pytest.raises(FileNotFoundError):
        PartitionLoader(manifest_path, root, tmp_path / "access.jsonl")
    # El reintento aparta el directorio incompleto (sin borrarlo) y confirma una snapshot nueva.
    res = build(tmp_path)
    q = res.manifest["incomplete_build_quarantined"]
    assert q and q.startswith(".incomplete-SNAP-TEST-") and (root / q).is_dir()
    assert verify_snapshot(res.manifest_path, root)["train_val"]
    assert sorted(p.name for p in root.iterdir()) == sorted(["SNAP-TEST", q])
    assert not (mdir / "SNAP-TEST.json.tmp").exists()


def test_train_validation_split_uses_manifest_cut(snap):
    res, tmp = snap
    loader = _loader(res, tmp)
    tr, va = loader.split_train_validation(loader.load_train_val("1d"))
    cut = res.manifest["cuts_ms"]["train_end"]
    assert tr["open_time"].max() < cut <= va["open_time"].min()
    assert va["open_time"].max() < res.manifest["cuts_ms"]["val_end"]


# --- TC-ML-016 / QA3-06: OOS y LOCKBOX sellados -----------------------------------------------

@pytest.mark.skipif(ROOT, reason="root ignora los permisos de archivo")
def test_qa3_06_sealed_files_cannot_be_read_directly(snap):
    res, _ = snap
    for part in ("oos", "lockbox"):
        with pytest.raises(PermissionError):
            SN.pq.read_table(res.data_dir / f"{part}.parquet")
        with pytest.raises(PermissionError):
            open(res.data_dir / f"{part}.parquet", "rb")
    assert res.manifest["file_modes"] == {"train_val": "0o444", "oos": "0o000", "lockbox": "0o000"}


def test_qa3_06_verify_snapshot_never_reads_sealed_partitions(snap, monkeypatch):
    res, tmp = snap
    read = []
    real = SN.sha256_file
    monkeypatch.setattr(SN, "sha256_file", lambda p: (read.append(Path(p).name), real(p))[1])
    verify_snapshot(res.manifest_path, tmp / "var" / "snapshots")
    assert read == ["train_val.parquet"]
    with pytest.raises(TypeError):
        verify_snapshot(res.manifest_path, tmp / "var" / "snapshots", partitions=("oos",))


def test_tc_ml_016_lockbox_and_oos_denied_without_grant_and_logged(snap, monkeypatch):
    res, tmp = snap
    import swingpilot.research.partitions as P
    opened = []
    real = P.pq.read_table
    monkeypatch.setattr(P.pq, "read_table", lambda path, *a, **k: (opened.append(Path(path).name), real(path, *a, **k))[1])
    loader = _loader(res, tmp)
    loader.load_train_val()
    for part in ("lockbox", "oos"):
        with pytest.raises(PartitionAccessError):
            loader.load_final(None, part)
    assert opened == ["train_val.parquet"]
    assert [(r["partition"], r["allowed"]) for r in loader.access_history()] == \
        [("train_val", True), ("lockbox", False), ("oos", False)]


def _advance_to_oos(reg, eid="EXP-T"):
    reg.create(eid, "prueba", actor="orquestador")
    reg.transition(eid, "DESIGN", actor="orquestador")
    reg.transition(eid, "PREREGISTERED", actor="orquestador",
                   evidence={"preregistration_sha256": "a" * 64, "min_history_ok": True})
    reg.transition(eid, "DATA_VALIDATION", actor="orquestador")
    reg.transition(eid, "DEVELOPMENT", actor="orquestador", evidence={"snapshot_verified": True})
    reg.transition(eid, "VALIDATION", actor="orquestador")
    reg.transition(eid, "OOS_EVALUATION", actor="propietario", evidence={"decision_ref": "DEC-999_eval.md"})


def grant(part="lockbox", eid="EXP-T", by="propietario", ref="DEC-999_eval.md"):
    return FinalEvaluationGrant(eid, part, "SNAP-TEST", by, ref)


def test_tc_ml_001_grant_conditions(snap):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    loader = _loader(res, tmp, reg)
    reg.create("EXP-T", "prueba", actor="orquestador")
    with pytest.raises(PartitionAccessError, match="OOS_EVALUATION"):
        loader.load_final(grant(), "lockbox")
    with pytest.raises(PartitionAccessError, match="propietario"):
        loader.load_final(grant(by="orquestador"), "lockbox")
    with pytest.raises(PartitionAccessError, match="no existe"):
        loader.load_final(grant(ref="DEC-000_x.md"), "lockbox")


def test_qa3_04_decision_must_be_plain_name_in_decisions_dir_and_cite_ids(snap):
    res, tmp = snap
    dec = _decisions(tmp, text="autoriza EXP-T sin más")     # no cita partición ni snapshot
    reg = ExperimentRegistry(tmp / "registry.jsonl", dec)
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)
    with pytest.raises(PartitionAccessError, match="no cita"):
        loader.load_final(grant(), "lockbox")
    other = tmp / "elsewhere"
    other.mkdir()
    (other / "DEC-005_x.md").write_text("EXP-T lockbox SNAP-TEST")
    for ref in (str(other / "DEC-005_x.md"), "../elsewhere/DEC-005_x.md", "/etc/../tmp/DEC-005_x.md"):
        with pytest.raises(PartitionAccessError, match="sin ruta"):
            loader.load_final(grant(ref=ref), "lockbox")
    (dec / "DEC-998_link.md").symlink_to(other / "DEC-005_x.md")
    with pytest.raises(PartitionAccessError, match="no existe"):
        loader.load_final(grant(ref="DEC-998_link.md"), "lockbox")
    assert not reg.consumed_partitions()


def test_qa3_04_registry_defaults_to_repo_decisions_dir(tmp_path):
    from swingpilot.research.experiments import REPO_DECISIONS_DIR
    reg = ExperimentRegistry(tmp_path / "r.jsonl")
    assert reg.decisions_dir == REPO_DECISIONS_DIR and REPO_DECISIONS_DIR.name == "decisions"
    assert (REPO_DECISIONS_DIR / "DEC-018_revision-impl3-q42-cr018-exp0001.md").is_file()


def test_qa3_03_antecedent_cannot_open_sealed_partitions(snap):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    for st in ("OOS_EVALUATION", "APPROVED", "HUMAN_REVIEW"):
        with pytest.raises(ExperimentError, match="no permitido"):
            reg.register_antecedent("EXP-T", "x", st, source="s", note="n")
    reg.register_antecedent("EXP-T", "x", "REJECTED", source="s", note="n")
    with pytest.raises(PartitionAccessError, match="antecedentes"):
        _loader(res, tmp, reg).load_final(grant(), "lockbox")


def test_tc_ml_007_019_lockbox_single_use_persisted_in_registry(snap):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)
    df = loader.load_final(grant(), "lockbox")
    assert len(df) > 0
    with pytest.raises(PartitionAccessError, match="consumido"):
        loader.load_final(grant(), "lockbox")
    # QA3-06: borrar el registro de accesos no «desconsume» el LOCKBOX
    loader.access_log.unlink()
    with pytest.raises(PartitionAccessError, match="consumido"):
        loader.load_final(grant(), "lockbox")
    rec = reg.consumed_lockboxes()
    assert rec == [{"snapshot_id": "SNAP-TEST", "snapshot_last_open_time": START + (DAYS - 1) * DAY_MS}]
    if not ROOT:
        with pytest.raises(PermissionError):
            open(res.data_dir / "lockbox.parquet", "rb")   # vuelve a quedar sellado


def _concurrent_loader(manifest_path, tmp, out, barrier):
    """Proceso hijo (spawn). Cada hijo comprueba el consumo y espera al otro antes de seguir: es
    el intercalado de la ronda 2. Con el bloqueo, el segundo no entra a la comprobación atómica
    hasta que el primero registra; la espera acotada evita un interbloqueo y no cambia el
    resultado."""
    import threading
    real = ExperimentRegistry.is_consumed

    def is_consumed_then_wait(self, *a, **k):
        result = real(self, *a, **k)
        try:
            barrier.wait(timeout=2)
        except threading.BrokenBarrierError:
            pass
        return result
    ExperimentRegistry.is_consumed = is_consumed_then_wait
    reg = ExperimentRegistry(tmp / "registry.jsonl", tmp / "decisions")
    loader = PartitionLoader(manifest_path, tmp / "var" / "snapshots", tmp / "access.jsonl", registry=reg)
    try:
        out.put(("LEIDO", len(loader.load_final(grant(), "lockbox"))))
    except PartitionAccessError as exc:
        out.put(("DENEGADO", str(exc)))
    except BaseException as exc:                                       # noqa: BLE001
        out.put(("ERROR", repr(exc)))


def test_qa3r2_03_two_concurrent_loaders_consume_lockbox_once(snap):
    import multiprocessing as mp
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    ctx = mp.get_context("spawn")
    barrier, out = ctx.Barrier(2), ctx.Queue()
    procs = [ctx.Process(target=_concurrent_loader, args=(res.manifest_path, tmp, out, barrier)) for _ in range(2)]
    for p in procs:
        p.start()
    results = sorted(out.get(timeout=120) for _ in procs)
    for p in procs:
        p.join(timeout=60)
    assert [r[0] for r in results] == ["DENEGADO", "LEIDO"], results
    assert "consumido" in results[0][1]
    consumed = [r for r in reg.consumed_partitions() if r["partition"] == "lockbox"]
    assert len(consumed) == 1                                     # un solo consumo en el registro
    log = [json.loads(x) for x in (tmp / "access.jsonl").read_text().splitlines()]
    assert sum(1 for r in log if r["partition"] == "lockbox" and r["allowed"]) == 1
    if not ROOT:
        with pytest.raises(PermissionError):
            open(res.data_dir / "lockbox.parquet", "rb")          # sigue sellado


def test_qa3r2_03_failed_read_keeps_partition_consumed_and_is_logged(snap):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)
    loader.manifest["files"]["lockbox"]["sha256"] = "0" * 64      # fuerza el fallo de lectura
    with pytest.raises(PartitionAccessError, match="SHA-256"):
        loader.load_final(grant(), "lockbox")
    assert reg.is_consumed("SNAP-TEST", "lockbox", "EXP-T")       # consumo conservador, documentado
    assert any("lectura fallida" in r["reason"] for r in loader.access_history())
    with pytest.raises(PartitionAccessError, match="consumido"):
        _loader(res, tmp, reg).load_final(grant(), "lockbox")


def test_tc_ml_019_new_lockbox_only_after_consumed_snapshot_end(tmp_path):
    cuts = compute_cuts(START, START + 1000 * DAY_MS)
    with pytest.raises(SnapshotError):
        check_new_lockbox(cuts, [{"snapshot_id": "SNAP-OLD", "snapshot_last_open_time": START + 900 * DAY_MS}])
    check_new_lockbox(cuts, [{"snapshot_id": "SNAP-OLD", "snapshot_last_open_time": START + 500 * DAY_MS}])
    # build_snapshot aplica la regla con los LOCKBOX consumidos que recibe (la CLI los lee del registro)
    with pytest.raises(SnapshotError, match="consumido"):
        build(tmp_path, consumed=[{"snapshot_id": "SNAP-OLD", "snapshot_last_open_time": START + 399 * DAY_MS}])


def test_cli_reads_consumed_lockboxes_from_registry(monkeypatch, tmp_path):
    from swingpilot.research import cli
    seen = {}
    monkeypatch.setattr(cli, "REGISTRY", tmp_path / "reg.jsonl")
    monkeypatch.setattr(cli, "build_snapshot", lambda *a, **k: seen.update(k) or (_ for _ in ()).throw(SystemExit(0)))
    reg = ExperimentRegistry(tmp_path / "reg.jsonl", _decisions(tmp_path))
    reg.record_partition_consumed(snapshot_id="SNAP-0000", partition="lockbox", experiment_id="EXP-X",
                                  snapshot_last_open_time=123, decision_ref="DEC-999_eval.md")
    with pytest.raises(SystemExit):
        cli.main(["build-snapshot", "--id", "SNAP-0009", "--confirm"])
    assert seen["consumed_lockboxes"] == [{"snapshot_id": "SNAP-0000", "snapshot_last_open_time": 123}]
    assert cli.main(["build-snapshot", "--id", "SNAP-0009"]) == 2   # sin --confirm no hace nada


def test_manifest_records_download_parameters(snap):
    res, _ = snap
    m = load_manifest(res.manifest_path)
    assert m["source"]["endpoint"] == "GET /api/v3/klines" and m["source"]["limit"] == 1000
    assert m["source"]["start_date"] == "2017-08-17" and m["lockbox"]["status"] == "SEALED"
    assert m["source"]["require_complete_download"] is True

