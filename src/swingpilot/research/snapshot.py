"""Snapshot histórica sellada de BTC/USDT (FEAT-015; REQ-G-109, REQ-G-101, REQ-G-102; DEC-013;
DEC-005 P10; DEC-017 Q46; TC-ML-015, TC-ML-017).

- Fuente: Binance REST público GET /api/v3/klines, 1d/4h/1h, desde 2017-08-17, limit=1000
  iterando con startTime; solo velas cerradas según la hora del servidor de Binance. La
  descarga de cada intervalo debe llegar hasta su última vela cerrada esperada: una respuesta
  truncada aborta la snapshot (QA3-02).
- Rango común [range_start, range_end): range_start = medianoche del primer día con datos;
  range_end = fin de la última vela D1 cerrada. La rejilla de cada intervalo cubre desde su
  primera vela (inicio de cotización, que debe caer en el primer día y se declara en el
  manifiesto) hasta range_end; una vela faltante dentro es una fila con OHLCV NaN, sin
  interpolar, y se cuenta.
- Particiones cronológicas 50/20/15/15 (Train/Val/OOS/LOCKBOX) con cortes por fecha en
  aritmética entera (QA3-10), idénticos para los tres intervalos. `train_val.parquet` contiene
  Train y Validation; el corte Train/Val queda en el manifiesto.
- Parquet fuera de Git (var/snapshots/<id>/). Se escribe en un directorio temporal y se
  renombra al final (QA3-15). `train_val` queda de solo lectura; `oos` y `lockbox` quedan sin
  permisos (0o000) y solo `PartitionLoader` los abre con una autorización válida (QA3-06).
  Manifiesto con SHA-256 por archivo y versiones de las librerías escritoras en el repositorio.
"""
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow
import pyarrow.parquet as pq

from swingpilot.market_data import BinancePublicClient, Candle, interval_ms, last_closed_open_time
from swingpilot.market_data.binance_public import KLINES_LIMIT
from swingpilot.market_data.candles import SYMBOL, closed_only, ms_to_iso

START_DATE = "2017-08-17"                 # DEC-013: primer dato de BTC/USDT en Binance
SPLIT_PCT = (50, 20, 15, 15)              # DEC-005 P10, en enteros (QA3-10)
PARTITIONS = ("train_val", "oos", "lockbox")
SEALED = ("oos", "lockbox")
SNAPSHOT_INTERVALS = ("1d", "4h", "1h")
MANIFEST_SCHEMA_VERSION = "1.1.0"
COLUMNS = ["interval", "open_time", "close_time", "open", "high", "low", "close", "volume"]
DAY_MS = 86_400_000
SNAPSHOT_ID = re.compile(r"^SNAP-[0-9]{4}$|^SNAP-TEST[A-Z0-9-]*$")
MODE_READONLY = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
MODE_SEALED = 0


class SnapshotError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _date_ms(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def compute_cuts(first_open_ms: int, end_exclusive_ms: int) -> dict[str, int]:
    """Cortes por fecha (medianoche UTC, hacia abajo) al 50%, 70% y 85% del rango; enteros."""
    span = end_exclusive_ms - first_open_ms
    if span <= 0:
        raise SnapshotError("rango vacío")

    def at(pct: int) -> int:
        return (first_open_ms + span * pct // 100) // DAY_MS * DAY_MS
    a, b, c = SPLIT_PCT[0], SPLIT_PCT[0] + SPLIT_PCT[1], SPLIT_PCT[0] + SPLIT_PCT[1] + SPLIT_PCT[2]
    cuts = {"train_end": at(a), "val_end": at(b), "oos_end": at(c)}
    if not first_open_ms < cuts["train_end"] < cuts["val_end"] < cuts["oos_end"] < end_exclusive_ms:
        raise SnapshotError(f"cortes no ordenados: {cuts}")
    return cuts


def to_grid_frame(interval: str, candles: list[Candle], first_open: int, end_exclusive: int) -> pd.DataFrame:
    """Rejilla completa de open_time en [first_open, end_exclusive); faltantes como NaN."""
    iv = interval_ms(interval)
    by_t = {c.open_time: c for c in candles}
    rows = []
    for t in range(first_open, end_exclusive, iv):
        c = by_t.get(t)
        if c is None:
            rows.append((interval, t, t + iv - 1) + (float("nan"),) * 5)
        else:
            rows.append((interval, t, c.close_time, c.open, c.high, c.low, c.close, c.volume))
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.astype({"open_time": "int64", "close_time": "int64"})


def partition_of(open_time: int, cuts: dict[str, int]) -> str:
    if open_time < cuts["val_end"]:
        return "train_val"
    if open_time < cuts["oos_end"]:
        return "oos"
    return "lockbox"


@dataclass
class SnapshotResult:
    manifest: dict
    manifest_path: Path
    data_dir: Path


def check_new_lockbox(cuts: dict[str, int], consumed_lockboxes: list[dict]) -> None:
    """REQ-G-109 (LOCKBOX consumido): con un LOCKBOX ya evaluado, solo los datos posteriores al
    final de aquella snapshot pueden formar un LOCKBOX nuevo (TC-ML-019)."""
    for rec in consumed_lockboxes:
        if cuts["oos_end"] <= rec["snapshot_last_open_time"]:
            raise SnapshotError(
                f"el LOCKBOX nuevo empezaría en {ms_to_iso(cuts['oos_end'])}, dentro de la snapshot "
                f"{rec['snapshot_id']} cuyo LOCKBOX ya fue consumido")


def build_snapshot(client: BinancePublicClient, snapshot_id: str, data_root: Path, manifest_dir: Path, *,
                   consumed_lockboxes: list[dict], start_date: str = START_DATE,
                   now=lambda: datetime.now(timezone.utc)) -> SnapshotResult:
    if not SNAPSHOT_ID.match(snapshot_id):
        raise SnapshotError(f"identificador de snapshot no válido: {snapshot_id!r}")
    data_root, manifest_dir = Path(data_root), Path(manifest_dir)
    data_dir = data_root / snapshot_id
    manifest_path = manifest_dir / f"{snapshot_id}.json"
    if data_dir.exists() or manifest_path.exists():
        raise SnapshotError(f"la snapshot {snapshot_id} ya existe: una snapshot no se reescribe")
    downloaded_at = now().strftime("%Y-%m-%dT%H:%M:%SZ")
    server_ms = client.server_time_ms()
    start_ms = _date_ms(start_date)
    candles: dict[str, list[Candle]] = {}
    for iv in SNAPSHOT_INTERVALS:
        end = last_closed_open_time(iv, server_ms)
        try:
            cs = closed_only(client.klines_range(iv, start_ms, end, require_end=True), server_ms)
        except Exception as exc:
            raise SnapshotError(f"descarga de {iv} fallida o incompleta: {exc}") from exc
        if not cs:
            raise SnapshotError(f"sin datos para {iv}")
        candles[iv] = cs
    range_start = min(cs[0].open_time for cs in candles.values()) // DAY_MS * DAY_MS
    range_end = candles["1d"][-1].open_time + DAY_MS
    first_open = {}
    frames = {}
    for iv in SNAPSHOT_INTERVALS:
        first = candles[iv][0].open_time
        if first >= range_start + DAY_MS:
            raise SnapshotError(f"{iv}: la primera vela ({ms_to_iso(first)}) no cae en el primer día del rango")
        if candles[iv][-1].open_time < range_end - interval_ms(iv):
            raise SnapshotError(f"{iv}: los datos no llegan al final del rango ({ms_to_iso(range_end)})")
        first_open[iv] = first
        frames[iv] = to_grid_frame(iv, [c for c in candles[iv] if c.open_time < range_end], first, range_end)
    cuts = compute_cuts(range_start, range_end)
    check_new_lockbox(cuts, consumed_lockboxes)

    data_root.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f".tmp-{snapshot_id}-", dir=data_root))
    try:
        files = {}
        for part in PARTITIONS:
            parts, stats = [], {}
            for iv in SNAPSHOT_INTERVALS:
                df = frames[iv]
                sel = df[df["open_time"].map(lambda t: partition_of(t, cuts)) == part]
                parts.append(sel)
                stats[iv] = {"rows": int(len(sel)), "gaps": int(sel["close"].isna().sum()),
                             "first_open_time_utc": ms_to_iso(int(sel["open_time"].min())) if len(sel) else None,
                             "last_open_time_utc": ms_to_iso(int(sel["open_time"].max())) if len(sel) else None}
                if not len(sel):
                    raise SnapshotError(f"{part}/{iv} vacío")
            out = pd.concat(parts, ignore_index=True)
            path = tmp_dir / f"{part}.parquet"
            pq.write_table(pyarrow.Table.from_pandas(out, preserve_index=False), path)
            files[part] = {"file": f"{part}.parquet", "sha256": sha256_file(path), "rows": int(len(out)),
                           "per_interval": stats}
            os.chmod(path, MODE_SEALED if part in SEALED else MODE_READONLY)
        os.rename(tmp_dir, data_dir)
    except BaseException:
        for p in tmp_dir.glob("*"):
            os.chmod(p, stat.S_IWUSR | stat.S_IRUSR)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    gaps_total = {iv: sum(files[p]["per_interval"][iv]["gaps"] for p in PARTITIONS) for iv in SNAPSHOT_INTERVALS}
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "downloaded_at_utc": downloaded_at,
        "binance_server_time_utc": ms_to_iso(server_ms),
        "source": {"base_url": client.base_url, "endpoint": "GET /api/v3/klines", "symbol": SYMBOL,
                   "intervals": list(SNAPSHOT_INTERVALS), "limit": KLINES_LIMIT, "start_date": start_date,
                   "only_closed_candles": True, "require_complete_download": True},
        "range": {"start_utc": ms_to_iso(range_start), "end_exclusive_utc": ms_to_iso(range_end),
                  "last_open_time_ms": range_end - DAY_MS},
        "listing_start": {iv: {"first_open_time_utc": ms_to_iso(first_open[iv]),
                               "rows_before_first_candle_excluded": (first_open[iv] - range_start) // interval_ms(iv)}
                          for iv in SNAPSHOT_INTERVALS},
        "split": {"train": 0.50, "validation": 0.20, "oos": 0.15, "lockbox": 0.15,
                  "method": "cronológico por fecha, aritmética entera; cortes idénticos para 1d, 4h y 1h"},
        "cuts_utc": {"train_end_exclusive": ms_to_iso(cuts["train_end"]),
                     "validation_end_exclusive": ms_to_iso(cuts["val_end"]),
                     "oos_end_exclusive": ms_to_iso(cuts["oos_end"])},
        "cuts_ms": cuts,
        "gaps_total": gaps_total,
        "files": files,
        "file_modes": {"train_val": "0o444", "oos": "0o000", "lockbox": "0o000"},
        "writer": {"python": platform.python_version(), "pandas": pd.__version__, "pyarrow": pyarrow.__version__},
        "lockbox": {"status": "SEALED", "rule": "no se carga en desarrollo; solo en la evaluación final única (REQ-G-109)"},
    }
    tmp_manifest = manifest_path.with_suffix(".json.tmp")
    tmp_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp_manifest, manifest_path)
    return SnapshotResult(manifest, manifest_path, data_dir)


def load_manifest(manifest_path: Path) -> dict:
    return json.loads(Path(manifest_path).read_text())


def verify_snapshot(manifest_path: Path, data_root: Path) -> dict[str, str]:
    """Recalcula el SHA-256 de `train_val` y falla si difiere del manifiesto (TC-ML-015).

    OOS y LOCKBOX no se verifican aquí: hashearlos es leerlos. Se verifican dentro de
    `PartitionLoader.load_final`, con autorización y registro (QA3-06)."""
    m = load_manifest(manifest_path)
    info = m["files"]["train_val"]
    actual = sha256_file(Path(data_root) / m["snapshot_id"] / info["file"])
    if actual != info["sha256"]:
        raise SnapshotError(f"train_val: SHA-256 {actual} ≠ manifiesto {info['sha256']}")
    return {"train_val": actual}
