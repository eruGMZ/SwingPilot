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


def _decisions(tmp, text="AUTORIZA: EXP-0900 OOS_EVALUATION\nAUTORIZA: EXP-0900 lockbox SNAP-TEST\nAUTORIZA: EXP-0900 oos SNAP-TEST\n"):
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
    h1 = _loader(res, tmp)._load_train_val_for_inspection("1h")
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
        _loader(res, tmp)._load_train_val_for_inspection()


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
    tr, va = loader.split_train_validation(loader._load_train_val_for_inspection("1d"))
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
    loader._load_train_val_for_inspection()
    for part in ("lockbox", "oos"):
        with pytest.raises(PartitionAccessError):
            loader.load_final(None, part)
    assert opened == ["train_val.parquet"]
    assert [(r["partition"], r["allowed"]) for r in loader.access_history()] == \
        [("train_val", True), ("lockbox", False), ("oos", False)]


def _advance_to_oos(reg, eid="EXP-0900"):
    reg.create(eid, "prueba", actor="orquestador")
    reg.transition(eid, "DESIGN", actor="orquestador")
    reg.transition(eid, "PREREGISTERED", actor="orquestador",
                   evidence={"preregistration_sha256": "a" * 64, "min_history_ok": True,
                             "trials_accounting": reg.trials_accounting(eid, ["A"])})        # CR-020
    reg.transition(eid, "DATA_VALIDATION", actor="orquestador")
    reg.transition(eid, "DEVELOPMENT", actor="orquestador", evidence={"snapshot_verified": True})
    reg.transition(eid, "VALIDATION", actor="orquestador")
    reg.begin_configuration_evaluation(eid, "A", actor="orquestador")                    # CR-020
    reg.transition(eid, "OOS_EVALUATION", actor="propietario",
                   evidence={"decision_ref": "DEC-999_eval.md", "selected_config_id": "A",
                             "selection_inputs_sha256": "0" * 64, "informed_by": []})


def grant(part="lockbox", eid="EXP-0900", by="propietario", ref="DEC-999_eval.md"):
    return FinalEvaluationGrant(eid, part, "SNAP-TEST", by, ref)


def test_tc_ml_001_grant_conditions(snap):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    loader = _loader(res, tmp, reg)
    reg.create("EXP-0900", "prueba", actor="orquestador")
    with pytest.raises(PartitionAccessError, match="OOS_EVALUATION"):
        loader.load_final(grant(), "lockbox")
    with pytest.raises(PartitionAccessError, match="propietario"):
        loader.load_final(grant(by="orquestador"), "lockbox")
    with pytest.raises(PartitionAccessError, match="no existe"):
        loader.load_final(grant(ref="DEC-000_x.md"), "lockbox")


def test_qa3_04_decision_must_be_plain_name_in_decisions_dir_and_cite_ids(snap):
    res, tmp = snap
    dec = _decisions(tmp, text="AUTORIZA: EXP-0900 OOS_EVALUATION\n")     # autoriza la transición, no la partición
    reg = ExperimentRegistry(tmp / "registry.jsonl", dec)
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)
    with pytest.raises(PartitionAccessError, match="no cita"):
        loader.load_final(grant(), "lockbox")
    other = tmp / "elsewhere"
    other.mkdir()
    (other / "DEC-005_x.md").write_text("AUTORIZA: EXP-0900 lockbox SNAP-TEST\n")
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
            reg.register_antecedent("EXP-0900", "x", st, source="s", note="n")
    reg.register_antecedent("EXP-0900", "x", "REJECTED", source="s", note="n")
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
    assert reg.is_consumed("SNAP-TEST", "lockbox", "EXP-0900")       # consumo conservador, documentado
    assert any("lectura fallida" in r["reason"] for r in loader.access_history())
    with pytest.raises(PartitionAccessError, match="consumido"):
        _loader(res, tmp, reg).load_final(grant(), "lockbox")


_SUBSTRING_DECISIONS = [
    # (partición pedida, texto de la decisión): todos pasaban la comprobación por subcadena
    ("oos", "AUTORIZA: EXP-0900 lockbox SNAP-TEST\nchoose"),            # «oos» dentro de «choose» (QA3R2-04)
    ("lockbox", "AUTORIZA: EXP-0900 oos SNAP-TEST\nNo se autoriza el lockbox."),
    ("lockbox", "AUTORIZA: EXP-09001 lockbox SNAP-TEST"),               # otro experimento que contiene el id
    ("lockbox", "AUTORIZA: EXP-0900 lockbox SNAP-TEST-2"),              # otra snapshot que contiene el id
    ("lockbox", "AUTORIZA: EXP-0900 LOCKBOX SNAP-TEST"),
    ("lockbox", "NO AUTORIZA: EXP-0900 lockbox SNAP-TEST"),
    ("lockbox", "> AUTORIZA: EXP-0900 lockbox SNAP-TEST"),
    ("lockbox", "AUTORIZA: EXP-0900 lockbox SNAP-TEST oos"),
    ("lockbox", "AUTORIZA: EXP-0900\nlockbox SNAP-TEST"),                # campos repartidos en líneas
    ("lockbox", "EXP-0900 lockbox SNAP-TEST"),
]


@pytest.mark.parametrize("part,text", _SUBSTRING_DECISIONS)
def test_qa3r2_04_partition_requires_exact_experiment_partition_snapshot(snap, part, text):
    res, tmp = snap
    dec = _decisions(tmp, text="AUTORIZA: EXP-0900 OOS_EVALUATION\n")             # solo la transición a OOS_EVALUATION
    (dec / "DEC-970_grant.md").write_text(text + "\n")
    reg = ExperimentRegistry(tmp / "registry.jsonl", dec)
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)
    with pytest.raises(PartitionAccessError, match="no cita exactamente"):
        loader.load_final(grant(part=part, ref="DEC-970_grant.md"), part)
    assert reg.consumed_partitions() == []                         # Fail-Closed: nada consumido
    assert [(r["partition"], r["allowed"]) for r in loader.access_history()] == [(part, False)]
    if not ROOT:
        with pytest.raises(PermissionError):
            open(res.data_dir / f"{part}.parquet", "rb")           # sigue sellada


@pytest.mark.parametrize("part", ["oos", "lockbox"])
def test_qa3r2_04_exact_partition_line_still_grants(snap, part):
    res, tmp = snap
    dec = _decisions(tmp, text="AUTORIZA: EXP-0900 OOS_EVALUATION\n")
    (dec / "DEC-971_grant.md").write_text(f"# Decisión\n\nAUTORIZA: EXP-0900 {part} SNAP-TEST\n")
    reg = ExperimentRegistry(tmp / "registry.jsonl", dec)
    _advance_to_oos(reg)
    assert len(_loader(res, tmp, reg).load_final(grant(part=part, ref="DEC-971_grant.md"), part)) > 0
    assert [r["partition"] for r in reg.consumed_partitions()] == [part]


@pytest.mark.parametrize("kw", [
    {"experiment_id": "EXP-X"}, {"experiment_id": "EXP-0900\n"}, {"experiment_id": None},
    {"partition": "LOCKBOX"}, {"partition": "train_val"}, {"partition": "lockbox "},
    {"snapshot_id": "SNAP-TEST/../x"}, {"snapshot_id": "SNAP-0001\n"}, {"snapshot_id": ""},
])
def test_qa3r2_04_claim_rejects_malformed_ids_without_writing(tmp_path, kw):
    reg = ExperimentRegistry(tmp_path / "reg.jsonl", _decisions(tmp_path))
    args = {"snapshot_id": "SNAP-TEST", "partition": "lockbox", "experiment_id": "EXP-0900",
            "snapshot_last_open_time": 1, "decision_ref": "DEC-999_eval.md", **kw}
    with pytest.raises(ExperimentError, match="no válid"):
        reg.claim_partition(**args)
    assert reg.records() == []


def test_qa3r2_04_decision_ok_rejects_malformed_request(tmp_path):
    reg = ExperimentRegistry(tmp_path / "reg.jsonl", _decisions(tmp_path))
    assert reg.decision_ok("DEC-999_eval.md", "EXP-0900", "lockbox", "SNAP-TEST") is None
    assert reg.decision_ok("DEC-999_eval.md", "EXP-0900", target_state="OOS_EVALUATION") is None
    for args in [("EXP-900", "lockbox", "SNAP-TEST"), ("EXP-0900", "LOCKBOX", "SNAP-TEST"),
                 ("EXP-0900", "lockbox", "SNAP-TEST\n"), ("EXP-0900", "lockbox", None), ("EXP-0900", None, "SNAP-TEST")]:
        assert reg.decision_ok("DEC-999_eval.md", *args) is not None, args
    assert reg.decision_ok("DEC-999_eval.md\n", "EXP-0900", target_state="OOS_EVALUATION") is not None


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
    reg.record_partition_consumed(snapshot_id="SNAP-0000", partition="lockbox", experiment_id="EXP-0999",
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



# --- QA3R2-08: sellado no efectivo o alterado; identificadores de snapshot en la CLI ------------

def _mode(path):
    import stat
    return stat.S_IMODE(os.stat(path).st_mode)


@pytest.mark.parametrize("bad", ["SNAP-1", "SNAP-00001", "snap-0001", "SNAP-0001\n", " SNAP-0001", "../SNAP-0001",
                                 "SNAP-0001/../x", "SNAP-TEST", ""])
@pytest.mark.parametrize("cmd", ["build-snapshot", "verify-snapshot"])
def test_qa3r2_08_cli_rejects_malformed_snapshot_id(monkeypatch, tmp_path, capsys, cmd, bad):
    from swingpilot.research import cli
    called = []
    monkeypatch.setattr(cli, "REGISTRY", tmp_path / "reg.jsonl")
    monkeypatch.setattr(cli, "MANIFEST_DIR", tmp_path / "manifests")
    monkeypatch.setattr(cli, "build_snapshot", lambda *a, **k: called.append("build"))
    monkeypatch.setattr(cli, "verify_snapshot", lambda *a, **k: called.append("verify"))
    argv = [cmd, "--id", bad] + (["--confirm"] if cmd == "build-snapshot" else [])
    assert cli.main(argv) == 2
    assert called == [] and "SNAP-NNNN" in capsys.readouterr().err
    assert not (tmp_path / "manifests").exists() and not (tmp_path / "reg.jsonl").exists()


def test_qa3r2_08_build_rejects_snapshot_id_with_trailing_newline(tmp_path):
    with pytest.raises(SnapshotError, match="no válido"):
        build(tmp_path, sid="SNAP-TEST\n")
    assert not (tmp_path / "var").exists() and not (tmp_path / "research").exists()


def test_qa3r2_08_manifest_with_invalid_snapshot_id_is_rejected(snap):
    res, tmp = snap
    for bad in ("../../outside", "SNAP-TEST\n", None):
        m = dict(res.manifest, snapshot_id=bad)
        p = tmp / "bad.json"
        p.write_text(json.dumps(m))
        with pytest.raises(SnapshotError, match="snapshot_id no válido"):
            PartitionLoader(p, tmp / "var" / "snapshots", tmp / "access.jsonl")
        with pytest.raises(SnapshotError, match="snapshot_id no válido"):
            verify_snapshot(p, tmp / "var" / "snapshots")


def test_qa3r2_08_ineffective_sealing_blocks_verify_and_loader(tmp_path, monkeypatch):
    # Simula un sistema de archivos que ignora 0o000: el proceso puede leer OOS/LOCKBOX.
    res = build(tmp_path)
    root = tmp_path / "var" / "snapshots"
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    with pytest.raises(SN.SealingError, match="no es efectivo para oos, lockbox"):
        verify_snapshot(res.manifest_path, root)
    with pytest.raises(SN.SealingError, match="no es efectivo para oos, lockbox"):
        PartitionLoader(res.manifest_path, root, tmp_path / "access.jsonl")
    assert not (tmp_path / "access.jsonl").exists()                # ni siquiera train_val


def test_qa3r2_08_cli_verify_fails_with_ineffective_sealing(tmp_path, monkeypatch, capsys):
    from swingpilot.research import cli
    res = build(tmp_path)
    monkeypatch.setattr(cli, "MANIFEST_DIR", res.manifest_path.parent)
    monkeypatch.setattr(cli, "DATA_ROOT", tmp_path / "var" / "snapshots")
    os.rename(res.manifest_path, res.manifest_path.with_name("SNAP-0042.json"))
    m = json.loads(res.manifest_path.with_name("SNAP-0042.json").read_text())
    m["snapshot_id"] = "SNAP-0042"
    res.manifest_path.with_name("SNAP-0042.json").write_text(json.dumps(m))
    os.rename(res.data_dir, res.data_dir.with_name("SNAP-0042"))
    assert cli.main(["verify-snapshot", "--id", "SNAP-0042"]) == 0      # control: sellado efectivo
    err = capsys.readouterr().err
    assert "AVISO" not in err and "ERROR" not in err
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    assert cli.main(["verify-snapshot", "--id", "SNAP-0042"]) == 1
    out = capsys.readouterr()
    assert "ERROR de sellado" in out.err and "oos, lockbox" in out.err and "OK" not in out.out


# --- QA3R2-08 (decisión del propietario): bloqueo cuando el sellado no se puede garantizar ------

class CountingBinance(SmallBinance):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def __call__(self, url):
        self.calls += 1
        return super().__call__(url)


def _snapshot_root_entries(tmp):
    root = tmp / "var" / "snapshots"
    return sorted(p.name for p in root.iterdir()) if root.exists() else None


def _orphan(tmp):
    orphan = tmp / "var" / "snapshots" / "SNAP-TEST"
    orphan.mkdir(parents=True)
    (orphan / "train_val.parquet").write_bytes(b"resto de una construccion interrumpida")
    return orphan


@pytest.mark.parametrize("cause", ["filesystem", "root"])
def test_qa3r2_08_preflight_blocks_before_download_and_quarantine(tmp_path, monkeypatch, cause):
    orphan = _orphan(tmp_path)
    if cause == "filesystem":
        monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    else:
        monkeypatch.setattr(SN.os, "geteuid", lambda: 0)
    fb = CountingBinance()
    with pytest.raises(SN.SealingError, match="root" if cause == "root" else "sigue siendo legible"):
        build(tmp_path, fb=fb)
    assert fb.calls == 0                                            # ninguna descarga
    assert _snapshot_root_entries(tmp_path) == ["SNAP-TEST"]        # ni cuarentena ni sonda ni temporales
    assert (orphan / "train_val.parquet").read_bytes().startswith(b"resto")
    assert not (tmp_path / "research" / "snapshots").exists()       # ningún manifiesto


def test_qa3r2_08_preflight_block_leaves_no_created_root(tmp_path, monkeypatch):
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    with pytest.raises(SN.SealingError):
        build(tmp_path)
    assert not (tmp_path / "var" / "snapshots").exists()            # el directorio creado se retira


def _readable_only_partitions(monkeypatch):
    # La sonda pasa (sellado efectivo en el directorio), pero OOS/LOCKBOX resultan legibles.
    real = os.access
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k:
                        True if Path(path).name in ("oos.parquet", "lockbox.parquet") else real(path, mode, *a, **k))


def test_qa3r2_08_final_check_failure_rolls_back_without_commit(tmp_path, monkeypatch):
    _readable_only_partitions(monkeypatch)
    fb = CountingBinance()
    with pytest.raises(SN.SealingError, match="no es efectivo para oos, lockbox"):
        build(tmp_path, fb=fb)
    assert fb.calls > 0                                             # falló tras descargar, antes de confirmar
    assert _snapshot_root_entries(tmp_path) == []                   # rollback: sin datos ni temporales
    mdir = tmp_path / "research" / "snapshots"
    assert not (mdir / "SNAP-TEST.json").exists() and not (mdir / "SNAP-TEST.json.tmp").exists()
    monkeypatch.undo()
    res = build(tmp_path)                                           # control: entorno conforme
    assert verify_snapshot(res.manifest_path, tmp_path / "var" / "snapshots")["train_val"]


def test_qa3r2_08_final_check_failure_keeps_orphan_quarantined_and_nothing_consumable(tmp_path, monkeypatch):
    _orphan(tmp_path)
    _readable_only_partitions(monkeypatch)
    with pytest.raises(SN.SealingError):
        build(tmp_path)
    entries = _snapshot_root_entries(tmp_path)
    assert len(entries) == 1 and entries[0].startswith(".incomplete-SNAP-TEST-")   # apartado, no borrado
    assert not (tmp_path / "research" / "snapshots" / "SNAP-TEST.json").exists()
    with pytest.raises(FileNotFoundError):
        PartitionLoader(tmp_path / "research" / "snapshots" / "SNAP-TEST.json", tmp_path / "var" / "snapshots",
                        tmp_path / "access.jsonl")


def test_qa3r2_08_probe_files_are_cleaned_up(tmp_path, monkeypatch):
    d = tmp_path / "d"
    d.mkdir()
    SN.check_sealing_supported(d)                                   # control conforme
    assert list(d.iterdir()) == []
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    with pytest.raises(SN.SealingError):
        SN.check_sealing_supported(d)
    assert list(d.iterdir()) == []


def test_qa3r2_08_loader_blocked_before_any_read_or_consumption(snap, monkeypatch):
    import swingpilot.research.partitions as P
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    opened = []
    real = P.pq.read_table
    monkeypatch.setattr(P.pq, "read_table", lambda src, *a, **k: (opened.append(src), real(src, *a, **k))[1])
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    with pytest.raises(SN.SealingError):
        _loader(res, tmp, reg)
    assert opened == [] and reg.consumed_partitions() == [] and not (tmp / "access.jsonl").exists()


def test_qa3r2_08_final_read_rechecks_sealing_before_consumption(snap, monkeypatch):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)                                 # creado en un entorno conforme
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    with pytest.raises(PartitionAccessError, match="sellado no efectivo"):
        loader.load_final(grant(), "lockbox")
    assert reg.consumed_partitions() == []                          # el bloqueo no consume
    assert [(r["partition"], r["allowed"]) for r in loader.access_history()] == [("lockbox", False)]
    monkeypatch.undo()
    assert len(loader.load_final(grant(), "lockbox")) > 0           # control: sigue disponible una vez
    assert [r["partition"] for r in reg.consumed_partitions()] == ["lockbox"]


@pytest.mark.parametrize("entry", ["verify", "loader"])
def test_qa3r2_08_leftover_readable_mode_is_resealed(snap, entry):
    res, tmp = snap
    path = res.data_dir / "lockbox.parquet"
    os.chmod(path, 0o400)                           # residuo de una lectura interrumpida
    with pytest.warns(SN.SealingWarning, match="lockbox: modo 0o400"):
        if entry == "verify":
            verify_snapshot(res.manifest_path, tmp / "var" / "snapshots")
        else:
            _loader(res, tmp)
    assert _mode(path) == 0
    assert _mode(res.data_dir / "oos.parquet") == 0


def test_qa3r2_08_effective_sealing_emits_no_warning(snap, recwarn):
    if ROOT:
        pytest.skip("root ignora los permisos de archivo")
    res, tmp = snap
    verify_snapshot(res.manifest_path, tmp / "var" / "snapshots")
    _loader(res, tmp)
    assert not [w for w in recwarn if issubclass(w.category, SN.SealingWarning)]
    assert res.sealing_warnings == []


_KILL_DURING_READ = """
import os, sys
from pathlib import Path
sys.path.insert(0, {unit!r})
import test_snapshot as T
import swingpilot.research.partitions as P
def die(*a, **k):
    os._exit(9)                           # SIGKILL simulado a mitad de la lectura autorizada
P.pq.read_table = die
tmp = Path({tmp!r})
reg = T.ExperimentRegistry(tmp / "registry.jsonl", tmp / "decisions")
loader = P.PartitionLoader(tmp / "research" / "snapshots" / "SNAP-TEST.json", tmp / "var" / "snapshots",
                           tmp / "access.jsonl", registry=reg)
loader.load_final(T.grant(), "lockbox")
"""


def test_qa3r2_08_kill_during_authorized_read_leaves_partition_sealed(snap):
    import subprocess
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    script = _KILL_DURING_READ.format(unit=str(Path(__file__).parent), tmp=str(tmp))
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 9, proc.stderr
    assert reg.is_consumed("SNAP-TEST", "lockbox", "EXP-0900")    # el consumo se registró antes de leer
    assert _mode(res.data_dir / "lockbox.parquet") == 0           # sin residuo 0o400 tras la muerte


@pytest.mark.parametrize("part", ["oos", "lockbox"])
def test_qa3r2_08_authorized_read_still_verifies_hash_and_reseals(snap, part):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)
    df = loader.load_final(grant(part=part), part)
    assert len(df) == res.manifest["files"][part]["rows"]
    assert _mode(res.data_dir / f"{part}.parquet") == 0


# --- CR-020 §C.3.2 (TC-ML-023): el cargador de Train+Val exige el inicio de evaluación registrado ---

def test_tc_ml_023_loader_delivers_train_val_only_for_registered_pair(snap):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    reg.create("EXP-0900", "prueba", actor="orquestador")
    reg.transition("EXP-0900", "DESIGN", actor="orquestador")
    reg.transition("EXP-0900", "PREREGISTERED", actor="orquestador",
                   evidence={"preregistration_sha256": "a" * 64, "min_history_ok": True,
                             "trials_accounting": reg.trials_accounting("EXP-0900", ["A"])})
    reg.transition("EXP-0900", "DATA_VALIDATION", actor="orquestador")
    reg.transition("EXP-0900", "DEVELOPMENT", actor="orquestador", evidence={"snapshot_verified": True})
    loader = _loader(res, tmp, reg)
    with pytest.raises(PartitionAccessError, match="sin inicio de evaluación"):
        loader.load_train_val_for_configuration("EXP-0900", "A", "1d")
    reg.begin_configuration_evaluation("EXP-0900", "A", actor="orquestador")
    df = loader.load_train_val_for_configuration("EXP-0900", "A", "1d")
    assert len(df) > 0 and set(df["interval"]) == {"1d"}
    assert [(r["partition"], r["allowed"]) for r in loader.access_history()] == [("train_val", False), ("train_val", True)]
    no_reg = _loader(res, tmp)
    with pytest.raises(PartitionAccessError, match="sin registro"):
        no_reg.load_train_val_for_configuration("EXP-0900", "A")


# --- A2 (CR-020 §C.3.2; decisión del propietario, opción B): única vía pública de Train+Val -----

import ast as _ast  # noqa: E402

_PRIVATE_LOADER = "_load_train_val_for_inspection"
_REPO = Path(__file__).resolve().parents[2]


def _external_loader_uses(source: str) -> list[int]:
    """Líneas que usan el cargador privado (o el antiguo nombre público) fuera de su definición."""
    out = []
    for node in _ast.walk(_ast.parse(source)):
        if isinstance(node, _ast.Attribute) and node.attr in (_PRIVATE_LOADER, "load_train_val"):
            out.append(node.lineno)
        if isinstance(node, _ast.Name) and node.id in (_PRIVATE_LOADER, "load_train_val"):
            out.append(node.lineno)
    return out


def test_a2_static_guard_no_external_use_of_private_loader():
    assert _external_loader_uses("x = loader._load_train_val_for_inspection('1d')") == [1]    # el detector detecta
    assert _external_loader_uses("x = loader.load_train_val()") == [1]
    assert _external_loader_uses("x = loader.load_train_val_for_configuration('E', 'A')") == []
    offenders = {}
    for root in ("src", "scripts"):
        for path in sorted((_REPO / root).rglob("*.py")):
            if path.name == "partitions.py" and path.parent.name == "research":
                continue
            hits = _external_loader_uses(path.read_text(encoding="utf-8"))
            if hits:
                offenders[str(path.relative_to(_REPO))] = hits
    assert offenders == {}, offenders


def test_a2_only_the_guarded_loader_is_public():
    public = {n for n in dir(PartitionLoader) if n.startswith("load_train_val")}
    assert public == {"load_train_val_for_configuration"}
    assert callable(getattr(PartitionLoader, _PRIVATE_LOADER))


def _dev_registry(tmp, eids=("EXP-0900",)):
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    for eid in eids:
        reg.create(eid, "prueba", actor="orquestador")
        reg.transition(eid, "DESIGN", actor="orquestador")
        reg.transition(eid, "PREREGISTERED", actor="orquestador",
                       evidence={"preregistration_sha256": "a" * 64, "min_history_ok": True,
                                 "trials_accounting": reg.trials_accounting(eid, ["A", "B"])})
        reg.transition(eid, "DATA_VALIDATION", actor="orquestador")
        reg.transition(eid, "DEVELOPMENT", actor="orquestador", evidence={"snapshot_verified": True})
    return reg


def _no_read(loader):
    reads = []
    loader._read = lambda part: reads.append(part) or (_ for _ in ()).throw(AssertionError("leyó datos"))
    return reads


def test_a2_malformed_evaluation_record_does_not_unlock_data(snap):
    res, tmp = snap
    reg = _dev_registry(tmp)
    reg._append({"kind": "CONFIGURATION_EVALUATED", "experiment_id": "EXP-0999", "config_id": "A",   # nunca creado
                 "preregistration_sha256": "a" * 64, "partition": "train_val", "actor": "manual"})
    loader = _loader(res, tmp, reg)
    reads = _no_read(loader)
    with pytest.raises(PartitionAccessError):
        loader.load_train_val_for_configuration("EXP-0999", "A")
    assert reads == [] and loader.access_history()[-1]["allowed"] is False


def test_a2_pair_must_match_exactly(snap):
    res, tmp = snap
    reg = _dev_registry(tmp, ("EXP-0900", "EXP-0901"))
    reg.begin_configuration_evaluation("EXP-0900", "A", actor="orquestador")
    loader = _loader(res, tmp, reg)
    reads = _no_read(loader)
    for eid, cfg in (("EXP-0900", "B"), ("EXP-0901", "A")):
        with pytest.raises(PartitionAccessError, match="sin inicio de evaluación"):
            loader.load_train_val_for_configuration(eid, cfg)
    assert reads == [] and [r["allowed"] for r in loader.access_history()] == [False, False]


@pytest.mark.parametrize("case", ["corrupt_json", "inconsistent_antecedent", "missing_file"])
def test_a2_unreadable_or_inconsistent_registry_denies_and_logs(snap, case):
    res, tmp = snap
    reg = _dev_registry(tmp)
    reg.begin_configuration_evaluation("EXP-0900", "A", actor="orquestador")
    if case == "corrupt_json":
        with open(reg.path, "a") as fh:
            fh.write('{"kind": "CONFIG')
    elif case == "inconsistent_antecedent":
        reg.register_antecedent("EXP-0001", "TF H4", "PENDING_DOCUMENTATION", source="s", note="n")   # sin procedencia
    else:
        reg.path.unlink()
    loader = _loader(res, tmp, reg)
    reads = _no_read(loader)
    with pytest.raises(PartitionAccessError):
        loader.load_train_val_for_configuration("EXP-0900", "A")
    assert reads == [] and loader.access_history()[-1]["allowed"] is False

