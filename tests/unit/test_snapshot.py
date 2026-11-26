"""FEAT-015 — TC-ML-001, TC-ML-015, TC-ML-016, TC-ML-017 y control de OOS/LOCKBOX.
Incluye las pruebas de QA3-02, 03, 04, 06, 09, 10 y 15, adaptadas a CR-023 (bloque B2): snapshot
de desarrollo (`train_val`, corte 5:2, `D_dev`) y snapshots de evaluación SINTÉTICAS escritas a
mano (no hay constructor de evaluación hasta B6).

Sin red: Binance simulado con un histórico corto.
"""
import hashlib
import json
import os
import struct
import sys
import urllib.parse
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swingpilot.market_data import BinancePublicClient, interval_ms  # noqa: E402
from swingpilot.research import partitions as P  # noqa: E402
from swingpilot.research import snapshot as SN  # noqa: E402
from swingpilot.research.experiments import ExperimentError, ExperimentRegistry  # noqa: E402
from swingpilot.research.partitions import (FinalEvaluationGrant, PartitionAccessError,  # noqa: E402
                                            PartitionLoader)
from test_cr023_b3_preregistration import register_confirmatory, store_for  # noqa: E402  (CR-023 B3)
from swingpilot.research.snapshot import (COLUMNS, DAY_MS, ReservedWindow, SnapshotError, _date_ms,  # noqa: E402
                                          build_snapshot, canonical_content_digest, compute_train_end,
                                          load_manifest, validate_manifest, verify_snapshot)

_B6_GATE_DEFAULT = P._FINAL_ACCESS_BLOCKED_UNTIL_B6        # valor de fábrica, leído al importar


@pytest.fixture(autouse=True)
def _historical_final_mechanism(monkeypatch):
    """B2-01: la restricción temporal hasta B6 bloquea todo `load_final`. Las pruebas históricas del
    mecanismo (autorización, consumo atómico, sellado, lectura) la desactivan para seguir
    cubriéndolo; las pruebas de la restricción la reactivan explícitamente."""
    monkeypatch.setattr(P, "_FINAL_ACCESS_BLOCKED_UNTIL_B6", False)


START = _date_ms("2017-08-17")
DAYS = 400
H = 3_600_000
SERVER = START + DAYS * DAY_MS + 5 * H + 7     # día 400, 05:00:00.007 UTC
DEV_DAYS = 300                                   # D_dev = día 300 (exclusivo)
D_DEV_MS = START + DEV_DAYS * DAY_MS
D_DEV = "2018-06-13"                             # = START + 300 días
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


def build(tmp, sid="SNAP-TEST", fb=None, d_dev=D_DEV, windows=()):
    return build_snapshot(BinancePublicClient(transport=fb or SmallBinance()), sid, tmp / "var" / "snapshots",
                          tmp / "research" / "snapshots", d_dev=d_dev, reserved_windows=list(windows))


@pytest.fixture
def snap(tmp_path):
    return build(tmp_path), tmp_path


# --- snapshot de evaluación SINTÉTICA (sin constructor hasta B6): escrita a mano ----------------

EVAL_CONTEXT_DAYS, EVAL_WINDOW_DAYS = 10, 10
EVAL_START = D_DEV_MS + EVAL_CONTEXT_DAYS * DAY_MS
EVAL_END = EVAL_START + EVAL_WINDOW_DAYS * DAY_MS
EVAL_LAST_OPEN = EVAL_END - H


def _synthetic_frame(first, end):
    rows = []
    for iv in SN.SNAPSHOT_INTERVALS:
        step = interval_ms(iv)
        for t in range(first, end, step):
            p = 1000.0 + (t // step) % 50
            rows.append((iv, t, t + step - 1, p, p + 5, p - 5, p + 1, 3.5))
    return pd.DataFrame(rows, columns=COLUMNS).astype({"open_time": "int64", "close_time": "int64"})


def _eval_manifest(sid, eid, part, files):
    return {
        "schema_version": SN.MANIFEST_SCHEMA_VERSION, "kind": "evaluation", "snapshot_id": sid,
        "window_id": f"{eid}/{part.upper()}", "d_dev": D_DEV, "d_dev_ms": D_DEV_MS,
        "window": {"start_ms": EVAL_START, "end_exclusive_ms": EVAL_END}, "context_start_ms": D_DEV_MS,
        "development_snapshot": {"snapshot_id": "SNAP-0001", "train_val_sha256": "a" * 64},
        "canonical_digest_algorithm": SN.CANONICAL_DIGEST_ALGORITHM,
        "range": {"last_open_time_ms": EVAL_LAST_OPEN}, "files": files,
        "file_modes": {"context": "0o000", part: "0o000"},
        "writer": {"python": "x", "pandas": pd.__version__, "pyarrow": SN.pyarrow.__version__},
    }


def make_eval(tmp, part="lockbox", sid="SNAP-TEST", eid="EXP-0900"):
    """Snapshot de evaluación sintética: context + partición en 0o000, manifiesto escrito a mano."""
    data_dir = tmp / "var" / "snapshots" / sid
    data_dir.mkdir(parents=True)
    spans = {"context": (D_DEV_MS, EVAL_START), part: (EVAL_START, EVAL_END)}
    files = {}
    for name, (a, b) in spans.items():
        df = _synthetic_frame(a, b)
        path = data_dir / f"{name}.parquet"
        SN.pq.write_table(SN.pyarrow.Table.from_pandas(df, preserve_index=False), path)
        files[name] = {"file": f"{name}.parquet", "sha256": SN.sha256_file(path), "rows": int(len(df)),
                       "canonical_digest": canonical_content_digest(df)}
        os.chmod(path, 0)
    m = _eval_manifest(sid, eid, part, files)
    mdir = tmp / "research" / "snapshots"
    mdir.mkdir(parents=True, exist_ok=True)
    mpath = mdir / f"{sid}.json"
    mpath.write_text(json.dumps(m, indent=2))
    return SN.SnapshotResult(m, mpath, data_dir, [])


@pytest.fixture
def esnap(tmp_path):
    return make_eval(tmp_path), tmp_path


def _decisions(tmp, text="AUTORIZA: EXP-0900 OOS_EVALUATION\nAUTORIZA: EXP-0900 lockbox SNAP-TEST\nAUTORIZA: EXP-0900 oos SNAP-TEST\n"):
    dec = tmp / "decisions"
    dec.mkdir(exist_ok=True)
    (dec / "DEC-999_eval.md").write_text(text)
    return dec


def _loader(res, tmp, reg=None):
    # CR-023 §C.3.3: el cargador de desarrollo exige el almacén de preregistros (temporal, junto al registro)
    return PartitionLoader(res.manifest_path, tmp / "var" / "snapshots", tmp / "access.jsonl", registry=reg,
                           prereg_store=store_for(reg) if reg is not None else None)


# --- TC-ML-015 / TC-ML-017 ---------------------------------------------------------------------

def test_tc_ml_015_development_snapshot_single_train_val_and_5_2_cut(snap):
    res, tmp = snap
    m = res.manifest
    assert m["kind"] == "development" and m["schema_version"] == "2.0.0" and m["window_id"] is None
    assert sorted(m["files"]) == ["train_val"] and len(m["files"]["train_val"]["sha256"]) == 64
    assert not {"oos.parquet", "lockbox.parquet", "context.parquet"} & {p.name for p in res.data_dir.iterdir()}
    assert set(m["writer"]) == {"python", "pandas", "pyarrow"}
    assert m["d_dev"] == D_DEV and m["d_dev_ms"] == D_DEV_MS
    cut = m["cuts_ms"]["train_end"]
    assert set(m["cuts_ms"]) == {"train_end"} and cut % DAY_MS == 0
    # Train = primeros 5/7, Validation = últimos 2/7 por fecha (CR-023 §C.1)
    assert (cut - START) // DAY_MS == DEV_DAYS * 5 // 7 == 214 and (D_DEV_MS - cut) // DAY_MS == 86
    assert m["range"]["end_exclusive_utc"] == "2018-06-13T00:00:00.000Z"
    # Corte idéntico para los tres intervalos: mismas filas Train/Val por fecha
    df = SN.pq.read_table(res.data_dir / "train_val.parquet").to_pandas()
    for iv, step in (("1d", DAY_MS), ("4h", 4 * H), ("1h", H)):
        d = df[df["interval"] == iv]
        assert d["open_time"].max() == D_DEV_MS - step
        assert (d["open_time"] < cut).sum() == (cut - d["open_time"].min()) // step
    assert m["files"]["train_val"]["per_interval"]["1d"]["rows"] == DEV_DAYS
    assert json.loads(res.manifest_path.read_text()) == m
    assert load_manifest(res.manifest_path) == m


def test_first_partial_day_is_declared_not_counted_as_gap(snap):
    res, _ = snap
    m = res.manifest
    assert m["listing_start"]["1h"] == {"first_open_time_utc": "2017-08-17T04:00:00.000Z",
                                        "rows_before_first_candle_excluded": 4}
    assert m["listing_start"]["4h"]["rows_before_first_candle_excluded"] == 1
    assert m["files"]["train_val"]["per_interval"]["1h"]["first_open_time_utc"] == "2017-08-17T04:00:00.000Z"
    # 1h: 300 días × 24 − 4 filas previas a la cotización
    assert m["files"]["train_val"]["per_interval"]["1h"]["rows"] == DEV_DAYS * 24 - 4


def test_tc_ml_017_gaps_are_nan_and_counted_consistently(snap):
    res, tmp = snap
    m = res.manifest
    assert m["gaps_total"] == {"1d": 0, "4h": 1, "1h": 1}
    for iv in ("1d", "4h", "1h"):   # QA3-09: el total coincide con la suma por archivo
        assert m["gaps_total"][iv] == sum(m["files"][p]["per_interval"][iv]["gaps"] for p in m["files"])
        assert m["files"]["train_val"]["canonical_digest"][iv]["gaps"] == m["gaps_total"][iv]
    h1 = _loader(res, tmp)._load_train_val_for_inspection("1h")
    row = h1[h1["open_time"] == START + 30 * DAY_MS + 3 * H]
    assert len(row) == 1 and row[["open", "high", "low", "close", "volume"]].isna().all(axis=None)


def test_only_closed_candles_in_snapshot(snap):
    res, _ = snap
    # CR-023: el rango termina en D_dev; el último open_time (máximo entre intervalos) es la última vela 1h
    assert res.manifest["range"]["last_open_time_ms"] == D_DEV_MS - H
    df = SN.pq.read_table(res.data_dir / "train_val.parquet").to_pandas()
    assert df["open_time"].max() == D_DEV_MS - H and (df["open_time"] < D_DEV_MS).all()


# --- QA3-02: descarga truncada o incompleta --------------------------------------------------

def test_qa3_02_truncated_download_aborts_without_sealing(tmp_path):
    with pytest.raises(SnapshotError, match="incompleta"):
        build(tmp_path, fb=SmallBinance(truncate_1h_after=300))
    assert not (tmp_path / "var" / "snapshots" / "SNAP-TEST").exists()
    assert not (tmp_path / "research" / "snapshots" / "SNAP-TEST.json").exists()


def test_qa3_02_missing_last_candle_aborts(tmp_path):
    with pytest.raises(SnapshotError):      # la última vela esperada es la anterior a D_dev (CR-023 §C.1)
        build(tmp_path, fb=SmallBinance(missing={("1h", D_DEV_MS - H)}))


def test_qa3_02_interval_starting_after_first_day_aborts(tmp_path):
    with pytest.raises(SnapshotError, match="primer día"):
        build(tmp_path, fb=SmallBinance(listing=START + 2 * DAY_MS))


# --- QA3-10 / CR-023 P1: corte Train:Validation 5:2 entero --------------------------------------

@pytest.mark.parametrize("ndays", [1000, 999, 1001, 3400, 3380, 3700, 7, 8])
def test_qa3_10_integer_5_2_cut(ndays):
    cut = compute_train_end(START, START + ndays * DAY_MS)
    assert cut == START + (ndays * 5 // 7) * DAY_MS
    assert cut % DAY_MS == 0 and START < cut < START + ndays * DAY_MS


def test_5_2_cut_is_identical_for_all_intervals_and_floors_to_midnight():
    # Rango con inicio a mitad de día (fracción de día): el corte baja a medianoche UTC, único para 1d/4h/1h
    cut = compute_train_end(START + 4 * H, START + 100 * DAY_MS)
    assert cut % DAY_MS == 0 and cut == (START + 4 * H + (100 * DAY_MS - 4 * H) * 5 // 7) // DAY_MS * DAY_MS


def test_cut_not_strictly_inside_range_is_rejected():
    with pytest.raises(SnapshotError):
        compute_train_end(START, START)
    with pytest.raises(SnapshotError):
        compute_train_end(START, START + DAY_MS)           # el corte cae en range_start


@pytest.mark.parametrize("d_dev,match", [
    ("2017-08-17", "posterior"),       # D_dev == inicio del rango
    ("2017-08-16", "posterior"),       # anterior al inicio
    ("2018-13-01", "no válido"), ("2018-6-13", "no válido"), ("2018-06-13T00:00", "no válido"), ("", "no válido"),
    ("2018-06-13\n", "no válido"),
    ("2018-06-14", None),              # control: válido (≤ hora del servidor)
    ("2019-09-26", "no llegan"),       # posterior a la hora del servidor (día 400 = 2018-09-21 05:00)
])
def test_d_dev_bounds(tmp_path, d_dev, match):
    if match is None:
        assert build(tmp_path, d_dev=d_dev).manifest["d_dev"] == d_dev
        return
    with pytest.raises(SnapshotError, match=match):
        build(tmp_path, d_dev=d_dev)
    assert not (tmp_path / "research").exists() and _snapshot_root_entries(tmp_path) in (None, [])


def test_d_dev_must_be_keyword_and_reserved_windows_required(tmp_path):
    args = (BinancePublicClient(transport=SmallBinance()), "SNAP-TEST", tmp_path / "v", tmp_path / "r")
    with pytest.raises(TypeError):
        build_snapshot(*args, reserved_windows=[])                      # sin d_dev
    with pytest.raises(TypeError):
        build_snapshot(*args, d_dev=D_DEV)                              # sin reserved_windows (sin valor por defecto)
    with pytest.raises(TypeError):
        build_snapshot(*args, d_dev=D_DEV, reserved_windows=[], consumed_lockboxes=[])   # parámetro retirado


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


def test_digest_in_manifest_matches_stored_parquet(snap):
    res, _ = snap
    df = SN.pq.read_table(res.data_dir / "train_val.parquet").to_pandas()
    assert res.manifest["files"]["train_val"]["canonical_digest"] == canonical_content_digest(df)
    assert res.manifest["canonical_digest_algorithm"] == SN.CANONICAL_DIGEST_ALGORITHM


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
        if calls["n"] == 1:                              # CR-023: un único archivo (train_val)
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
    assert va["open_time"].max() < D_DEV_MS                  # Validation termina en D_dev (CR-023)


# --- TC-ML-016 / QA3-06: OOS y LOCKBOX sellados -----------------------------------------------

@pytest.mark.skipif(ROOT, reason="root ignora los permisos de archivo")
def test_qa3_06_sealed_files_cannot_be_read_directly(esnap):
    res, tmp = esnap
    for part in ("context", "lockbox"):                       # CR-023 §C.6.2: context también 0o000
        with pytest.raises(PermissionError):
            SN.pq.read_table(res.data_dir / f"{part}.parquet")
        with pytest.raises(PermissionError):
            open(res.data_dir / f"{part}.parquet", "rb")
    assert res.manifest["file_modes"] == {"context": "0o000", "lockbox": "0o000"}
    dev = build(tmp, sid="SNAP-TEST2")
    assert dev.manifest["file_modes"] == {"train_val": "0o444"}
    assert _mode(dev.data_dir / "train_val.parquet") == 0o444


def test_qa3_06_verify_snapshot_never_reads_sealed_partitions(esnap, monkeypatch):
    eres, etmp = esnap
    res, tmp = build(etmp, sid="SNAP-TEST2"), etmp
    read = []
    real = SN.sha256_file
    monkeypatch.setattr(SN, "sha256_file", lambda p: (read.append(Path(p).name), real(p))[1])
    verify_snapshot(res.manifest_path, tmp / "var" / "snapshots")
    assert read == ["train_val.parquet"]
    with pytest.raises(TypeError):
        verify_snapshot(res.manifest_path, tmp / "var" / "snapshots", partitions=("oos",))
    # evaluation: solo sellado; ni hash ni lectura de ningún archivo
    read.clear()
    opened = []
    monkeypatch.setattr(SN.pq, "read_table", lambda *a, **k: opened.append(a))
    assert verify_snapshot(eres.manifest_path, etmp / "var" / "snapshots") == {}
    assert read == [] and opened == []


def test_tc_ml_016_lockbox_and_oos_denied_without_grant_and_logged(esnap, monkeypatch):
    res, tmp = esnap
    import swingpilot.research.partitions as P
    opened = []
    real = P.pq.read_table
    monkeypatch.setattr(P.pq, "read_table", lambda path, *a, **k: (opened.append(Path(path).name), real(path, *a, **k))[1])
    loader = _loader(res, tmp)
    with pytest.raises(PartitionAccessError, match="rechaza snapshots kind='evaluation'"):
        loader._load_train_val_for_inspection()              # CR-023: el cargador de desarrollo rechaza evaluación
    for part in ("lockbox", "oos"):
        with pytest.raises(PartitionAccessError):
            loader.load_final(None, part)
    assert opened == []
    assert [(r["partition"], r["allowed"]) for r in loader.access_history()] == \
        [("train_val", False), ("lockbox", False), ("oos", False)]



def legacy_freeze_check():
    """Solo pruebas heredadas (CR-020/CR-021): congelación sin las comprobaciones de ET-1, construida
    deliberadamente con la credencial privada (B3-01: el registro ya no acepta un invocable arbitrario)."""
    from swingpilot.research.experiments import _FREEZE_CHECK_KEY, FreezeCheck
    return FreezeCheck(_FREEZE_CHECK_KEY, lambda records, experiment_id, evidence: None)

def _advance_to_oos(reg, eid="EXP-0900"):
    reg.create(eid, "prueba", actor="orquestador")
    reg.transition(eid, "DESIGN", actor="orquestador")
    reg.transition(eid, "PREREGISTERED", actor="orquestador", freeze_check=legacy_freeze_check(),   # CR-023
                   evidence={"preregistration_sha256": "a" * 64, "min_history_ok": True,
                             "independence_class": "CONFIRMATORY",
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


def test_tc_ml_001_grant_conditions(esnap):
    res, tmp = esnap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    loader = _loader(res, tmp, reg)
    reg.create("EXP-0900", "prueba", actor="orquestador")
    with pytest.raises(PartitionAccessError, match="OOS_EVALUATION"):
        loader.load_final(grant(), "lockbox")
    with pytest.raises(PartitionAccessError, match="propietario"):
        loader.load_final(grant(by="orquestador"), "lockbox")
    with pytest.raises(PartitionAccessError, match="no existe"):
        loader.load_final(grant(ref="DEC-000_x.md"), "lockbox")


def test_qa3_04_decision_must_be_plain_name_in_decisions_dir_and_cite_ids(esnap):
    res, tmp = esnap
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


def test_qa3_03_antecedent_cannot_open_sealed_partitions(esnap):
    res, tmp = esnap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    for st in ("OOS_EVALUATION", "APPROVED", "HUMAN_REVIEW"):
        with pytest.raises(ExperimentError, match="no permitido"):
            reg.register_antecedent("EXP-0900", "x", st, source="s", note="n")
    reg.register_antecedent("EXP-0900", "x", "REJECTED", source="s", note="n")
    with pytest.raises(PartitionAccessError, match="antecedentes"):
        _loader(res, tmp, reg).load_final(grant(), "lockbox")


def test_tc_ml_007_019_lockbox_single_use_persisted_in_registry(esnap):
    res, tmp = esnap
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
    assert rec == [{"snapshot_id": "SNAP-TEST", "snapshot_last_open_time": EVAL_LAST_OPEN}]   # forma del registro intacta
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
    P._FINAL_ACCESS_BLOCKED_UNTIL_B6 = False                          # mecanismo histórico (B2-01)
    reg = ExperimentRegistry(tmp / "registry.jsonl", tmp / "decisions")
    loader = PartitionLoader(manifest_path, tmp / "var" / "snapshots", tmp / "access.jsonl", registry=reg)
    try:
        out.put(("LEIDO", len(loader.load_final(grant(), "lockbox"))))
    except PartitionAccessError as exc:
        out.put(("DENEGADO", str(exc)))
    except BaseException as exc:                                       # noqa: BLE001
        out.put(("ERROR", repr(exc)))


def test_qa3r2_03_two_concurrent_loaders_consume_lockbox_once(esnap):
    import multiprocessing as mp
    res, tmp = esnap
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


def test_qa3r2_03_failed_read_keeps_partition_consumed_and_is_logged(esnap):
    res, tmp = esnap
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
def test_qa3r2_04_partition_requires_exact_experiment_partition_snapshot(tmp_path, part, text):
    res, tmp = make_eval(tmp_path, part), tmp_path
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
def test_qa3r2_04_exact_partition_line_still_grants(tmp_path, part):
    res, tmp = make_eval(tmp_path, part), tmp_path
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


# --- CR-023 §C.6.5: ventanas reservadas (interfaz inyectada; fuente autoritativa pendiente en B5) ---

def _w(start_ms, wid="EXP-0900/OOS", end_ms=None):
    return ReservedWindow(wid, start_ms, end_ms if end_ms is not None else start_ms + 10 * DAY_MS)


@pytest.mark.parametrize("start", [D_DEV_MS - H, D_DEV_MS - DAY_MS, START + DAY_MS])
def test_reserved_window_reached_by_snapshot_is_rejected_and_nothing_written(tmp_path, start):
    fb = CountingBinance()
    with pytest.raises(SnapshotError, match="ventana reservada EXP-0900/OOS"):
        build(tmp_path, fb=fb, windows=[_w(start)])
    assert _snapshot_root_entries(tmp_path) in (None, [])        # ni directorio, ni temporal, ni cuarentena
    assert not (tmp_path / "research").exists()                  # ningún manifiesto


def test_reserved_window_check_uses_every_interval_not_only_1d(tmp_path):
    # 1d termina en D_dev − 1 día, 1h en D_dev − 1 h: una ventana que empieza a D_dev − 2 h solo la alcanza 1h
    with pytest.raises(SnapshotError, match="1h"):
        build(tmp_path, windows=[_w(D_DEV_MS - 2 * H)])


def test_reserved_window_at_or_after_d_dev_is_accepted_and_recorded(tmp_path):
    res = build(tmp_path, windows=[_w(D_DEV_MS), _w(D_DEV_MS + 40 * DAY_MS, "EXP-0900/LOCKBOX")])
    assert res.manifest["reserved_windows_checked"] == ["EXP-0900/OOS", "EXP-0900/LOCKBOX"]
    assert build(tmp_path, sid="SNAP-TEST2", windows=[]).manifest["reserved_windows_checked"] == []


@pytest.mark.parametrize("bad", [
    lambda: ReservedWindow("EXP-0900", 1, 2), lambda: ReservedWindow("EXP-0900/OOS", 2, 2),
    lambda: ReservedWindow("EXP-0900/OOS", 1.5, 2), lambda: ReservedWindow("EXP-0900/OOS", True, 2)])
def test_reserved_window_construction_is_validated(bad):
    with pytest.raises(SnapshotError):
        bad()


def test_non_window_items_in_reserved_windows_are_rejected(tmp_path):
    with pytest.raises(SnapshotError, match="ReservedWindow"):
        build(tmp_path, windows=[(D_DEV_MS, D_DEV_MS + 1)])
    assert not (tmp_path / "var").exists()


def test_manifest_records_download_parameters(snap):
    res, _ = snap
    m = load_manifest(res.manifest_path)
    assert m["source"]["endpoint"] == "GET /api/v3/klines" and m["source"]["limit"] == 1000
    assert m["source"]["start_date"] == "2017-08-17" and m["kind"] == "development"
    assert "lockbox" not in m and "oos" not in m["files"]       # CR-023: la snapshot de desarrollo no tiene LOCKBOX
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
    monkeypatch.setattr(cli, "MANIFEST_DIR", tmp_path / "manifests")
    monkeypatch.setattr(cli, "build_snapshot", lambda *a, **k: called.append("build"))
    monkeypatch.setattr(cli, "verify_snapshot", lambda *a, **k: called.append("verify"))
    monkeypatch.setattr(cli, "reserved_windows_provider", lambda: called.append("provider") or [])
    argv = [cmd, "--id", bad] + (["--d-dev", D_DEV, "--confirm"] if cmd == "build-snapshot" else [])
    assert cli.main(argv) == 2
    assert called == [] and "SNAP-NNNN" in capsys.readouterr().err
    assert not (tmp_path / "manifests").exists()


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
    # Simula un sistema de archivos que ignora 0o000: el proceso puede leer context/OOS/LOCKBOX.
    res = make_eval(tmp_path)
    root = tmp_path / "var" / "snapshots"
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    with pytest.raises(SN.SealingError, match="no es efectivo para context, lockbox"):
        verify_snapshot(res.manifest_path, root)
    with pytest.raises(SN.SealingError, match="no es efectivo para context, lockbox"):
        PartitionLoader(res.manifest_path, root, tmp_path / "access.jsonl")
    assert not (tmp_path / "access.jsonl").exists()                # ni siquiera train_val


def test_qa3r2_08_development_snapshot_has_no_sealed_files_and_never_keyerrors(snap, monkeypatch):
    res, tmp = snap
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    assert SN.enforce_sealing(res.data_dir, res.manifest["files"]) == []      # sin context/oos/lockbox: nada que sellar
    assert verify_snapshot(res.manifest_path, tmp / "var" / "snapshots")["train_val"]
    _loader(res, tmp)


def test_qa3r2_08_cli_verify_fails_with_ineffective_sealing(tmp_path, monkeypatch, capsys):
    from swingpilot.research import cli
    res = make_eval(tmp_path, sid="SNAP-0042")
    monkeypatch.setattr(cli, "MANIFEST_DIR", res.manifest_path.parent)
    monkeypatch.setattr(cli, "DATA_ROOT", tmp_path / "var" / "snapshots")
    assert cli.main(["verify-snapshot", "--id", "SNAP-0042"]) == 0      # control: sellado efectivo
    cap = capsys.readouterr()
    assert "AVISO" not in cap.err and "ERROR" not in cap.err and "sin lectura ni hash" in cap.out
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    assert cli.main(["verify-snapshot", "--id", "SNAP-0042"]) == 1
    out = capsys.readouterr()
    assert "ERROR de sellado" in out.err and "context, lockbox" in out.err and "OK" not in out.out


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
    # La sonda previa pasa, pero la comprobación final del sellado dentro de la construcción falla
    # (una snapshot de desarrollo no tiene archivos sellados: se simula el fallo de esa comprobación).
    def failing(data_dir, files):
        raise SN.SealingError("el sellado 0o000 no es efectivo para context, lockbox (simulado)")
    monkeypatch.setattr(SN, "enforce_sealing", failing)


def test_qa3r2_08_final_check_failure_rolls_back_without_commit(tmp_path, monkeypatch):
    _readable_only_partitions(monkeypatch)
    fb = CountingBinance()
    with pytest.raises(SN.SealingError, match="no es efectivo para context, lockbox"):
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


def test_qa3r2_08_loader_blocked_before_any_read_or_consumption(esnap, monkeypatch):
    import swingpilot.research.partitions as P
    res, tmp = esnap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    opened = []
    real = P.pq.read_table
    monkeypatch.setattr(P.pq, "read_table", lambda src, *a, **k: (opened.append(src), real(src, *a, **k))[1])
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    with pytest.raises(SN.SealingError):
        _loader(res, tmp, reg)
    assert opened == [] and reg.consumed_partitions() == [] and not (tmp / "access.jsonl").exists()


def test_qa3r2_08_final_read_rechecks_sealing_before_consumption(esnap, monkeypatch):
    res, tmp = esnap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)                                 # creado en un entorno conforme
    monkeypatch.setattr(SN.os, "access", lambda path, mode, *a, **k: True)
    with pytest.raises(PartitionAccessError, match="sellado no efectivo"):
        loader.load_final(grant(), "lockbox")
    assert reg.consumed_partitions() == []                          # el bloqueo no consume
    assert [(r["partition"], r["allowed"]) for r in loader.access_history()] == [("lockbox", False)]
    monkeypatch.undo()
    monkeypatch.setattr(P, "_FINAL_ACCESS_BLOCKED_UNTIL_B6", False)  # undo() también deshizo el fixture (B2-01)
    assert len(loader.load_final(grant(), "lockbox")) > 0           # control: sigue disponible una vez
    assert [r["partition"] for r in reg.consumed_partitions()] == ["lockbox"]


@pytest.mark.parametrize("entry", ["verify", "loader"])
def test_qa3r2_08_leftover_readable_mode_is_resealed(esnap, entry):
    res, tmp = esnap
    path = res.data_dir / "lockbox.parquet"
    os.chmod(path, 0o400)                           # residuo de una lectura interrumpida
    with pytest.warns(SN.SealingWarning, match="lockbox: modo 0o400"):
        if entry == "verify":
            verify_snapshot(res.manifest_path, tmp / "var" / "snapshots")
        else:
            _loader(res, tmp)
    assert _mode(path) == 0
    assert _mode(res.data_dir / "context.parquet") == 0


def test_qa3r2_08_effective_sealing_emits_no_warning(esnap, recwarn):
    if ROOT:
        pytest.skip("root ignora los permisos de archivo")
    for res, tmp in (esnap, (build(esnap[1], sid="SNAP-TEST2"), esnap[1])):
        verify_snapshot(res.manifest_path, tmp / "var" / "snapshots")
        _loader(res, tmp)
        assert res.sealing_warnings == []
    assert not [w for w in recwarn if issubclass(w.category, SN.SealingWarning)]


_KILL_DURING_READ = """
import os, sys
from pathlib import Path
sys.path.insert(0, {unit!r})
import test_snapshot as T
import swingpilot.research.partitions as P
def die(*a, **k):
    os._exit(9)                           # SIGKILL simulado a mitad de la lectura autorizada
P.pq.read_table = die
P._FINAL_ACCESS_BLOCKED_UNTIL_B6 = False  # mecanismo histórico (B2-01)
tmp = Path({tmp!r})
reg = T.ExperimentRegistry(tmp / "registry.jsonl", tmp / "decisions")
loader = P.PartitionLoader(tmp / "research" / "snapshots" / "SNAP-TEST.json", tmp / "var" / "snapshots",
                           tmp / "access.jsonl", registry=reg)
loader.load_final(T.grant(), "lockbox")
"""


def test_qa3r2_08_kill_during_authorized_read_leaves_partition_sealed(esnap):
    import subprocess
    res, tmp = esnap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    script = _KILL_DURING_READ.format(unit=str(Path(__file__).parent), tmp=str(tmp))
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 9, proc.stderr
    assert reg.is_consumed("SNAP-TEST", "lockbox", "EXP-0900")    # el consumo se registró antes de leer
    assert _mode(res.data_dir / "lockbox.parquet") == 0           # sin residuo 0o400 tras la muerte


@pytest.mark.parametrize("part", ["oos", "lockbox"])
def test_qa3r2_08_authorized_read_still_verifies_hash_and_reseals(tmp_path, part):
    res, tmp = make_eval(tmp_path, part), tmp_path
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)
    df = loader.load_final(grant(part=part), part)
    assert len(df) == res.manifest["files"][part]["rows"]
    assert _mode(res.data_dir / f"{part}.parquet") == 0 and _mode(res.data_dir / "context.parquet") == 0


# --- CR-020 §C.3.2 (TC-ML-023): el cargador de Train+Val exige el inicio de evaluación registrado ---

def test_tc_ml_023_loader_delivers_train_val_only_for_registered_pair(snap):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    reg.create("EXP-0900", "prueba", actor="orquestador")
    reg.transition("EXP-0900", "DESIGN", actor="orquestador")
    register_confirmatory(reg, "EXP-0900", ("A",))        # CR-023: contenido en el almacén + clase CONFIRMATORY
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
        register_confirmatory(reg, eid, ("A", "B"))       # CR-023: contenido en el almacén + clase CONFIRMATORY
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



# --- CR-023 §C.6.5: digest canónico de contenido -------------------------------------------------

def _row(iv, t, step, o=1.0, h=2.0, lo=0.5, c=1.5, v=3.0):
    return (iv, t, t + step - 1, o, h, lo, c, v)


def _frame(rows):
    return pd.DataFrame(rows, columns=COLUMNS).astype({"open_time": "int64", "close_time": "int64"})


def _manual_digest(rows):
    """Referencia independiente de la función: serialización explícita con struct y hashlib."""
    h = hashlib.sha256()
    for iv, t, ct, *nums in sorted(rows, key=lambda r: (r[0], r[1])):
        h.update(bytes([len(iv)]) + iv.encode("ascii") + struct.pack(">d", float(t)) + struct.pack(">d", float(ct)))
        for x in nums:
            h.update(b"\x7f\xf8" + b"\x00" * 6 if x != x else struct.pack(">d", x))
    return h.hexdigest()


def test_digest_known_vector_and_structure():
    rows = [_row("1h", 3_600_000, H), _row("1h", 0, H), _row("1h", 2 * H, H, o=float("nan"), h=float("nan"),
                                                            lo=float("nan"), c=float("nan"), v=float("nan"))]
    d = canonical_content_digest(_frame(rows))
    assert list(d) == ["1h"] and d["1h"]["rows"] == 3 and d["1h"]["gaps"] == 1
    assert d["1h"]["sha256"] == _manual_digest(rows)
    # Vector fijo: una sola fila, calculable a mano (cualquier cambio de formato lo rompe)
    one = canonical_content_digest(_frame([_row("1d", 0, DAY_MS)]))
    raw = (b"\x02" + b"1d" + struct.pack(">d", 0.0) + struct.pack(">d", DAY_MS - 1.0)
           + b"".join(struct.pack(">d", x) for x in (1.0, 2.0, 0.5, 1.5, 3.0)))
    assert one["1d"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert one["1d"]["sha256"] == "b2f0550ab0852b40a91231ed0dce0ef778445ecc27f1bca6a6abb6d7d4c60c08"      # valor fijado: un cambio de formato lo rompe


def test_digest_is_order_independent_and_per_interval():
    a = [_row("1d", 0, DAY_MS), _row("1d", DAY_MS, DAY_MS), _row("4h", 0, 4 * H), _row("1h", 0, H)]
    d1 = canonical_content_digest(_frame(a))
    d2 = canonical_content_digest(_frame(list(reversed(a))))
    d3 = canonical_content_digest(_frame(a[:2]))
    assert d1 == d2 and sorted(d1) == ["1d", "1h", "4h"]
    assert d3["1d"] == d1["1d"] and d1["1d"]["rows"] == 2 and d1["4h"]["rows"] == 1   # un intervalo no afecta a otro


def test_digest_nan_is_canonical_regardless_of_nan_payload():
    quiet = float("nan")
    other = struct.unpack(">d", bytes.fromhex("7ff8000000000abc"))[0]         # NaN con carga distinta
    neg = struct.unpack(">d", bytes.fromhex("fff8000000000000"))[0]           # NaN con signo
    base = [_row("1h", 0, H, o=quiet, h=quiet, lo=quiet, c=quiet, v=quiet)]
    variants = [[_row("1h", 0, H, o=other, h=neg, lo=other, c=neg, v=other)]]
    assert canonical_content_digest(_frame(base)) == canonical_content_digest(_frame(variants[0]))
    # Pero 0.0 y -0.0 NO se normalizan (sin otra normalización)
    z = canonical_content_digest(_frame([_row("1h", 0, H, o=0.0)]))
    nz = canonical_content_digest(_frame([_row("1h", 0, H, o=-0.0)]))
    assert z != nz
    # Cualquier cambio de valor cambia el digest
    assert canonical_content_digest(_frame([_row("1h", 0, H, c=1.5000000001)])) != \
        canonical_content_digest(_frame([_row("1h", 0, H, c=1.5)]))


@pytest.mark.parametrize("bad_ts", [2 ** 53, -(2 ** 53), 2 ** 62])
def test_digest_rejects_timestamps_out_of_range(bad_ts):
    for row in (("1h", bad_ts, 0, 1.0, 2.0, 0.5, 1.5, 3.0), ("1h", 0, bad_ts, 1.0, 2.0, 0.5, 1.5, 3.0)):
        with pytest.raises(SnapshotError, match="2\\*\\*53"):
            canonical_content_digest(_frame([row]))
    ok = ("1h", 2 ** 53 - 2, 2 ** 53 - 1, 1.0, 2.0, 0.5, 1.5, 3.0)           # límite válido
    assert canonical_content_digest(_frame([ok]))["1h"]["rows"] == 1


def test_digest_rejects_non_integer_timestamps_duplicates_and_missing_columns():
    df = _frame([_row("1h", 0, H)])
    with pytest.raises(SnapshotError, match="entero"):
        canonical_content_digest(df.astype({"open_time": "float64"}))
    with pytest.raises(SnapshotError, match="duplicada"):
        canonical_content_digest(_frame([_row("1h", 0, H), _row("1h", 0, H)]))
    with pytest.raises(SnapshotError, match="faltan columnas"):
        canonical_content_digest(df.drop(columns=["volume"]))
    with pytest.raises(SnapshotError, match="intervalo"):
        canonical_content_digest(_frame([_row("1ñ", 0, H)]))


# --- validate_manifest / load_manifest por kind ----------------------------------------------------

def test_validate_manifest_accepts_both_kinds(snap):
    res, tmp = snap
    assert validate_manifest(res.manifest) is res.manifest
    for part in ("oos", "lockbox"):
        ev = make_eval(tmp, part, sid=f"SNAP-TEST-{part.upper()}")
        assert load_manifest(ev.manifest_path)["window_id"] == f"EXP-0900/{part.upper()}"


def _mut(m, **changes):
    out = json.loads(json.dumps(m))
    for k, v in changes.items():
        if v is _DEL:
            out.pop(k, None)
        else:
            out[k] = v
    return out


_DEL = object()


def test_legacy_and_unknown_kind_manifests_are_rejected(snap):
    res, tmp = snap
    legacy = _mut(res.manifest, kind=_DEL, schema_version="1.2.0")
    for bad in (legacy, _mut(res.manifest, kind=_DEL), _mut(res.manifest, kind="live"), _mut(res.manifest, kind=None),
                _mut(res.manifest, schema_version="1.2.0")):
        with pytest.raises(SnapshotError, match="manifiesto no válido"):
            validate_manifest(bad)
        p = tmp / "legacy.json"
        p.write_text(json.dumps(bad))
        with pytest.raises(SnapshotError):
            load_manifest(p)
        with pytest.raises(SnapshotError):
            verify_snapshot(p, tmp / "var" / "snapshots")
        with pytest.raises(SnapshotError):
            PartitionLoader(p, tmp / "var" / "snapshots", tmp / "access.jsonl")
    with pytest.raises(SnapshotError):
        validate_manifest(["no es un objeto"])


def _bad_dev_cases(m):
    f = m["files"]["train_val"]
    return {
        "extra_oos": _mut(m, files={**m["files"], "oos": f}),
        "extra_lockbox": _mut(m, files={**m["files"], "lockbox": f}),
        "extra_context": _mut(m, files={**m["files"], "context": f}),
        "window_id_set": _mut(m, window_id="EXP-0900/OOS"),
        "no_d_dev": _mut(m, d_dev=_DEL), "bad_d_dev": _mut(m, d_dev="2018-06-31"),
        "d_dev_ms_mismatch": _mut(m, d_dev_ms=m["d_dev_ms"] + 1),
        "no_cuts": _mut(m, cuts_ms={}), "cut_after_d_dev": _mut(m, cuts_ms={"train_end": m["d_dev_ms"]}),
        "modes_with_sealed": _mut(m, file_modes={"train_val": "0o444", "oos": "0o000"}),
        "no_digest": _mut(m, files={"train_val": {k: v for k, v in f.items() if k != "canonical_digest"}}),
        "digest_missing_interval": _mut(m, files={"train_val": {**f, "canonical_digest": {
            k: v for k, v in f["canonical_digest"].items() if k != "4h"}}}),
        "bad_sha": _mut(m, files={"train_val": {**f, "sha256": "xyz"}}),
        "no_algorithm": _mut(m, canonical_digest_algorithm=_DEL),
        "no_last_open": _mut(m, range={"start_ms": m["range"]["start_ms"]}),
        "files_missing": _mut(m, files=_DEL),
    }


def test_development_manifest_schema_rejects_malformed(snap):
    res, _ = snap
    for name, bad in _bad_dev_cases(res.manifest).items():
        with pytest.raises(SnapshotError, match="no válido"):
            validate_manifest(bad)


def _bad_eval_cases(m):
    c, part = m["files"]["context"], m["files"]["lockbox"]
    return {
        "bad_window_id": _mut(m, window_id="EXP-0900/oos"), "window_id_none": _mut(m, window_id=None),
        "window_id_no_exp": _mut(m, window_id="OOS"), "window_id_newline": _mut(m, window_id="EXP-0900/OOS\n"),
        "train_val_present": _mut(m, files={**m["files"], "train_val": part}),
        "no_context": _mut(m, files={"lockbox": part}),
        "wrong_partition_for_window": _mut(m, window_id="EXP-0900/OOS"),         # files = context + lockbox
        "both_partitions": _mut(m, files={**m["files"], "oos": part}),
        "context_start_not_d_dev": _mut(m, context_start_ms=m["d_dev_ms"] + DAY_MS),
        "window_before_d_dev": _mut(m, window={"start_ms": m["d_dev_ms"] - 1, "end_exclusive_ms": EVAL_END}),
        "window_empty": _mut(m, window={"start_ms": EVAL_START, "end_exclusive_ms": EVAL_START}),
        "no_window": _mut(m, window=_DEL),
        "no_dev_ref": _mut(m, development_snapshot=_DEL),
        "dev_ref_bad_sha": _mut(m, development_snapshot={"snapshot_id": "SNAP-0001", "train_val_sha256": "a"}),
        "dev_ref_bad_id": _mut(m, development_snapshot={"snapshot_id": "x", "train_val_sha256": "a" * 64}),
        "no_digest_part": _mut(m, files={"context": c, "lockbox": {k: v for k, v in part.items()
                                                                  if k != "canonical_digest"}}),
        "no_digest_context": _mut(m, files={"context": {k: v for k, v in c.items() if k != "canonical_digest"},
                                            "lockbox": part}),
        "modes_readable": _mut(m, file_modes={"context": "0o444", "lockbox": "0o000"}),
        "modes_missing_context": _mut(m, file_modes={"lockbox": "0o000"}),
        "no_last_open": _mut(m, range={}),
        "no_algorithm": _mut(m, canonical_digest_algorithm=""),
        "d_dev_mismatch": _mut(m, d_dev_ms=m["d_dev_ms"] + 1),
    }


@pytest.mark.parametrize("part", ["oos", "lockbox"])
def test_evaluation_manifest_schema_accepts_valid_and_rejects_malformed(tmp_path, part):
    ev = make_eval(tmp_path, part)
    validate_manifest(ev.manifest)
    cases = _bad_eval_cases(make_eval(tmp_path, "lockbox", sid="SNAP-TEST9").manifest)
    for name, bad in cases.items():
        if part == "oos" and name == "wrong_partition_for_window":
            continue
        with pytest.raises(SnapshotError, match="no válido"):
            validate_manifest(bad)


# --- cargadores de desarrollo rechazan evaluación; load_final rechaza desarrollo ---------------------

def test_development_loaders_reject_evaluation_snapshot_logged_without_reading(esnap):
    res, tmp = esnap
    reg = _dev_registry(tmp)
    reg.begin_configuration_evaluation("EXP-0900", "A", actor="orquestador")        # el par SÍ está registrado
    loader = _loader(res, tmp, reg)
    reads = _no_read(loader)
    calls = [lambda: loader.load_train_val_for_configuration("EXP-0900", "A", "1d"),
             lambda: loader.load_train_val_for_configuration("EXP-0900", "A"),
             lambda: loader._load_train_val_for_inspection("1d"),
             lambda: loader.split_train_validation(pd.DataFrame({"open_time": [1]}))]
    for call in calls:
        with pytest.raises(PartitionAccessError, match="kind='evaluation'"):
            call()
    assert reads == []
    hist = loader.access_history()
    assert len(hist) == 4 and all(r["allowed"] is False and r["partition"] == "train_val" for r in hist)


def test_development_loaders_reject_manifest_without_kind_fail_closed(snap):
    """Un manifiesto sin `kind` (p. ej. un doble que elude `load_manifest`) no es de desarrollo."""
    res, tmp = snap
    reg = _dev_registry(tmp)
    reg.begin_configuration_evaluation("EXP-0900", "A", actor="orquestador")
    loader = _loader(res, tmp, reg)
    loader.manifest = {k: v for k, v in loader.manifest.items() if k != "kind"}
    reads = _no_read(loader)
    for call in (lambda: loader.load_train_val_for_configuration("EXP-0900", "A"),
                 lambda: loader._load_train_val_for_inspection(),
                 lambda: loader.split_train_validation(pd.DataFrame({"open_time": [1]}))):
        with pytest.raises(PartitionAccessError, match="kind=None"):
            call()
    assert reads == []
    assert all(r["allowed"] is False for r in loader.access_history())


def test_load_final_on_development_snapshot_is_denied_logged_and_not_consumed(snap):
    res, tmp = snap
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    _advance_to_oos(reg)
    loader = _loader(res, tmp, reg)
    reads = _no_read(loader)
    for part in ("oos", "lockbox"):
        with pytest.raises(PartitionAccessError, match="desarrollo"):
            loader.load_final(grant(part=part), part)
        with pytest.raises(PartitionAccessError):
            loader.load_final(None, part)
    with pytest.raises(PartitionAccessError):
        loader.load_final(grant(part="context"), "context")
    assert reads == [] and reg.consumed_partitions() == []
    assert all(r["allowed"] is False for r in loader.access_history()) and len(loader.access_history()) == 5


def test_load_final_requires_partition_and_experiment_to_match_manifest_window(tmp_path):
    res = make_eval(tmp_path, "lockbox")
    dec = _decisions(tmp_path, text="AUTORIZA: EXP-0900 OOS_EVALUATION\nAUTORIZA: EXP-0900 oos SNAP-TEST\n"
                                    "AUTORIZA: EXP-0900 lockbox SNAP-TEST\n")
    reg = ExperimentRegistry(tmp_path / "registry.jsonl", dec)
    _advance_to_oos(reg)
    loader = _loader(res, tmp_path, reg)
    with pytest.raises(PartitionAccessError, match="no coincide con la ventana"):
        loader.load_final(grant(part="oos"), "oos")            # la snapshot es de la ventana LOCKBOX
    assert reg.consumed_partitions() == []
    assert len(loader.load_final(grant(), "lockbox")) > 0     # coincide: se concede y consume como siempre
    rec = reg.consumed_partitions()
    assert len(rec) == 1 and set(rec[0]) == set(reg.consumed_partitions()[0])
    assert "window_id" not in rec[0]                           # sin campos nuevos en PARTITION_CONSUMED


# --- B2-01: restricción temporal Fail-Closed de la evaluación final hasta B6 ------------------------

def test_b2_01_final_access_gate_is_active_by_default():
    assert _B6_GATE_DEFAULT is True


@pytest.mark.parametrize("part", ["oos", "lockbox"])
def test_b2_01_valid_grant_on_synthetic_evaluation_snapshot_is_denied_without_consumption(tmp_path, monkeypatch,
                                                                                          part):
    """Manifiesto 2.0.0 válido, autorización exacta del propietario y experimento en OOS_EVALUATION:
    todo lo que hoy concedería el mecanismo vigente. Hasta B6 se deniega antes del consumo."""
    monkeypatch.setattr(P, "_FINAL_ACCESS_BLOCKED_UNTIL_B6", True)
    res = make_eval(tmp_path, part)
    reg = ExperimentRegistry(tmp_path / "registry.jsonl", _decisions(tmp_path))
    _advance_to_oos(reg)
    before = (tmp_path / "registry.jsonl").read_bytes()
    loader = _loader(res, tmp_path, reg)
    reads = _no_read(loader)
    for _ in range(2):                                          # repetible: nada queda consumido
        with pytest.raises(PartitionAccessError, match="bloqueada hasta B6"):
            loader.load_final(grant(part=part), part)
    assert reads == []
    assert reg.consumed_partitions() == []
    assert (tmp_path / "registry.jsonl").read_bytes() == before   # ningún registro nuevo
    hist = loader.access_history()
    assert len(hist) == 2 and all(r["allowed"] is False and "B6" in r["reason"] for r in hist)
    assert _mode(res.data_dir / f"{part}.parquet") == 0 and _mode(res.data_dir / "context.parquet") == 0


def test_b2_01_gate_preserves_earlier_denial_reasons(tmp_path, monkeypatch):
    """La restricción va al final: los motivos de denegación vigentes no cambian."""
    monkeypatch.setattr(P, "_FINAL_ACCESS_BLOCKED_UNTIL_B6", True)
    res = make_eval(tmp_path, "lockbox")
    reg = ExperimentRegistry(tmp_path / "registry.jsonl", _decisions(tmp_path))
    _advance_to_oos(reg)
    loader = _loader(res, tmp_path, reg)
    with pytest.raises(PartitionAccessError, match="sin autorización"):
        loader.load_final(None, "lockbox")
    with pytest.raises(PartitionAccessError, match="no es del propietario"):
        loader.load_final(grant(by="orquestador"), "lockbox")
    assert reg.consumed_partitions() == []


# --- CLI ---------------------------------------------------------------------------------------------

def test_cli_build_requires_d_dev_and_confirm(monkeypatch, capsys):
    from swingpilot.research import cli
    called = []
    monkeypatch.setattr(cli, "build_snapshot", lambda *a, **k: called.append(k))
    monkeypatch.setattr(cli, "reserved_windows_provider", lambda: called.append("provider") or [])
    with pytest.raises(SystemExit) as e:
        cli.main(["build-snapshot", "--id", "SNAP-0009", "--confirm"])          # sin --d-dev
    assert e.value.code == 2
    assert cli.main(["build-snapshot", "--id", "SNAP-0009", "--d-dev", D_DEV]) == 2   # sin --confirm
    assert called == []


def test_cli_build_fails_closed_before_download_while_window_source_is_pending(monkeypatch, tmp_path, capsys):
    from swingpilot.research import cli
    monkeypatch.setattr(cli, "DATA_ROOT", tmp_path / "var")
    monkeypatch.setattr(cli, "MANIFEST_DIR", tmp_path / "man")
    monkeypatch.setattr(cli, "BinancePublicClient", lambda *a, **k: (_ for _ in ()).throw(AssertionError("descargó")))
    assert cli.main(["build-snapshot", "--id", "SNAP-0009", "--d-dev", D_DEV, "--confirm"]) == 1
    assert "pendiente (B5)" in capsys.readouterr().err
    assert not (tmp_path / "var").exists() and not (tmp_path / "man").exists()


def test_cli_build_passes_d_dev_and_injected_windows(monkeypatch, capsys):
    from swingpilot.research import cli
    seen = {}
    win = [_w(D_DEV_MS + DAY_MS)]
    monkeypatch.setattr(cli, "reserved_windows_provider", lambda: win)
    monkeypatch.setattr(cli, "BinancePublicClient", lambda *a, **k: "client")

    def fake_build(client, sid, data_root, manifest_dir, **k):
        seen.update(k, client=client, sid=sid)
        raise SnapshotError("ventana reservada simulada")
    monkeypatch.setattr(cli, "build_snapshot", fake_build)
    assert cli.main(["build-snapshot", "--id", "SNAP-0009", "--d-dev", D_DEV, "--confirm"]) == 1
    assert seen["d_dev"] == D_DEV and seen["reserved_windows"] == win and seen["sid"] == "SNAP-0009"
    assert "ventana reservada simulada" in capsys.readouterr().err


def test_cli_build_and_verify_development_end_to_end(monkeypatch, tmp_path, capsys):
    from swingpilot.research import cli
    fake = BinancePublicClient(transport=SmallBinance())
    monkeypatch.setattr(cli, "DATA_ROOT", tmp_path / "var" / "snapshots")
    monkeypatch.setattr(cli, "MANIFEST_DIR", tmp_path / "research" / "snapshots")
    monkeypatch.setattr(cli, "BinancePublicClient", lambda: fake)
    monkeypatch.setattr(cli, "reserved_windows_provider", lambda: [])
    assert cli.main(["build-snapshot", "--id", "SNAP-0042", "--d-dev", D_DEV, "--confirm"]) == 0
    out = capsys.readouterr().out
    assert "train_val" in out and "oos" not in out
    assert cli.main(["verify-snapshot", "--id", "SNAP-0042"]) == 0
    assert "train_val" in capsys.readouterr().out
    bad = tmp_path / "research" / "snapshots" / "SNAP-0042.json"
    m = json.loads(bad.read_text())
    m.pop("kind")
    bad.write_text(json.dumps(m))
    assert cli.main(["verify-snapshot", "--id", "SNAP-0042"]) == 1               # heredado: Fail-Closed
    assert "kind" in capsys.readouterr().err
