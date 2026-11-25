"""Snapshot histórica sellada de BTC/USDT (FEAT-015; REQ-G-109, REQ-G-101, REQ-G-102; DEC-013;
DEC-005 P10; DEC-017 Q46; CR-023 §C.1, §C.6, §C.7; TC-ML-015, TC-ML-016, TC-ML-017).

CR-023 (bloque B2, lado de desarrollo): hay dos clases de snapshot, distinguidas por `kind` en el
manifiesto (esquema 2.0.0).

- `development`: región de desarrollo [range_start, D_dev) con `D_dev` exclusivo (medianoche UTC),
  un único `train_val.parquet` (columna `interval`) y corte Train:Validation 5:2 por fecha, en
  aritmética entera, idéntico para 1d, 4h y 1h. No tiene `oos` ni `lockbox`; el constructor
  `build_snapshot` solo construye este tipo. Rechaza el cierre si algún intervalo termina en o
  después del inicio de una ventana reservada activa (comprobación INYECTADA: la fuente
  autoritativa de ventanas pendiente de B5; no es una garantía operativa).
- `evaluation`: `context` + (`oos` | `lockbox`) de una ventana `EXP-NNNN/OOS|LOCKBOX`, sin
  `train_val`. En B2 solo existe su validación de esquema (`validate_manifest`) y el sellado;
  su constructor, la lectura del `context`, la regla OOS-antes-que-LOCKBOX y las comprobaciones
  V pertenecen a bloques posteriores (B6).
- Un manifiesto sin `kind`, con `kind` desconocido o de esquema anterior se rechaza
  (Fail-Closed).

Descarga y confirmación (sin cambios respecto a FEAT-015):
- Fuente: Binance REST público GET /api/v3/klines, 1d/4h/1h, desde 2017-08-17, limit=1000
  iterando con startTime; solo velas cerradas según la hora del servidor de Binance. La
  descarga de cada intervalo debe llegar hasta su última vela cerrada esperada (la anterior a
  `D_dev`): una respuesta truncada aborta la snapshot (QA3-02).
- Rango común [range_start, D_dev): range_start = medianoche del primer día con datos. La
  rejilla de cada intervalo cubre desde su primera vela (inicio de cotización, que debe caer en
  el primer día y se declara en el manifiesto) hasta `D_dev`; una vela faltante dentro es una
  fila con OHLCV NaN, sin interpolar, y se cuenta.
- Digest canónico de contenido (CR-023 §C.6.5): SHA-256 por intervalo de las filas ordenadas por
  (`interval`, `open_time`), con los números en IEEE-754 binary64 big-endian y un único NaN
  canónico; se calcula en memoria antes de escribir y sellar y se guarda con filas y huecos.
- Parquet fuera de Git (var/snapshots/<id>/). Se escribe en un directorio temporal y se
  renombra al final (QA3-15). `train_val` queda de solo lectura (0o444); `context`, `oos` y
  `lockbox` (snapshots de evaluación) quedan sin permisos (0o000). Manifiesto con SHA-256 por
  archivo y versiones de las librerías escritoras en el repositorio.
- Confirmación (QA3R2-02): el manifiesto es el punto de confirmación; una snapshot solo es
  consumible (PartitionLoader, verify_snapshot) si su manifiesto existe. Orden: manifiesto
  temporal → renombrado del directorio de datos → `os.replace` del manifiesto (atómico). Un
  fallo en el proceso en cualquier punto deshace el directorio de datos y el manifiesto
  temporal. Si el proceso muere sin poder deshacer, queda un directorio de datos sin
  manifiesto: no es consumible, y el siguiente intento lo aparta como
  `.incomplete-<id>-<marca>` (sin borrarlo) y lo deja anotado en el manifiesto nuevo.
- Sellado (QA3R2-08; decisión del propietario 2026-11-24, sin CR): el modo 0o000 solo protege
  si el sistema lo aplica. Se exige un usuario distinto de root, un sistema de archivos con
  permisos POSIX y un sellado verificado; si no se puede garantizar, se BLOQUEA (SealingError),
  sin excepciones ni mecanismo de omisión. La sonda previa de `build_snapshot` (archivo
  temporal en 0o000 + `os.access`, siempre borrado) se ejecuta antes de descargar y antes de
  apartar un directorio huérfano. `enforce_sealing` actúa por tipo: sella los archivos
  presentes entre `context`/`oos`/`lockbox` (una snapshot de desarrollo no tiene ninguno) y
  nunca falla por clave ausente. Si un archivo sellado tiene otro modo (p. ej. 0o400 por un
  SIGKILL durante una lectura), se vuelve a sellar a 0o000 y se avisa (SealingWarning); solo se
  bloquea si tras volver a sellarlo sigue siendo legible.
- Identificadores (QA3R2-08): `valid_snapshot_id` usa `fullmatch` (sin salto de línea final).
  `load_manifest` rechaza un manifiesto cuyo `snapshot_id` no sea válido, porque de él se
  deriva la ruta de los datos.
"""
import hashlib
import json
import math
import os
import platform
import re
import shutil
import stat
import struct
import tempfile
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq

from swingpilot.market_data import BinancePublicClient, Candle, interval_ms, last_closed_open_time
from swingpilot.market_data.binance_public import KLINES_LIMIT
from swingpilot.market_data.candles import SYMBOL, closed_only, ms_to_iso

START_DATE = "2017-08-17"                 # DEC-013: primer dato de BTC/USDT en Binance
TRAIN_VAL_RATIO = (5, 2)                  # CR-023 §C.1 (P1): Train = primeros 5/7, Validation = últimos 2/7
SEALED = ("oos", "lockbox")               # particiones de evaluación final consumibles (registro de experimentos)
SEALED_FILES = ("context", "oos", "lockbox")   # archivos sellados 0o000 (snapshots de evaluación)
SNAPSHOT_INTERVALS = ("1d", "4h", "1h")
KIND_DEVELOPMENT, KIND_EVALUATION = "development", "evaluation"
MANIFEST_SCHEMA_VERSION = "2.0.0"           # 2.0.0: `kind`, D_dev, digests canónicos (CR-023)
COLUMNS = ["interval", "open_time", "close_time", "open", "high", "low", "close", "volume"]
DAY_MS = 86_400_000
SNAPSHOT_ID = re.compile(r"^SNAP-[0-9]{4}$|^SNAP-TEST[A-Z0-9-]*$")   # usar con fullmatch (QA3R2-08)
WINDOW_ID = re.compile(r"EXP-[0-9]{4}/(OOS|LOCKBOX)")                 # usar con fullmatch (CR-023 §C.1)
D_DEV_FORMAT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
MODE_READONLY = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
MODE_SEALED = 0
CANONICAL_NAN = b"\x7f\xf8\x00\x00\x00\x00\x00\x00"       # 0x7FF8000000000000
CANONICAL_DIGEST_ALGORITHM = (
    "canonical-content-v1: sha256 por intervalo de las filas ordenadas por (interval, open_time); por fila: "
    "longitud del intervalo (1 byte) + intervalo ASCII + open_time, close_time, open, high, low, close, volume "
    "como IEEE-754 binary64 big-endian ('>d'); marcas de tiempo enteras con |x| < 2**53; cualquier NaN como "
    "0x7FF8000000000000; sin otra normalización")
_DIGEST_FIELDS = ("open_time", "close_time", "open", "high", "low", "close", "volume")


class SnapshotError(RuntimeError):
    pass


class SealingWarning(UserWarning):
    """Un archivo sellado tenía otro modo y se volvió a sellar (QA3R2-08)."""


class SealingError(SnapshotError):
    """No se puede garantizar el sellado efectivo de los archivos sellados: se bloquea (QA3R2-08)."""


@dataclass(frozen=True)
class ReservedWindow:
    """Ventana de evaluación ACTIVA (reservada, ni consumida ni liberada), en ms UTC [start, end).

    Interfaz INYECTADA (CR-023 §C.6.5, «Separación verificable»): quien llama es responsable de
    entregar solo ventanas activas. La fuente autoritativa de ventanas reservadas está pendiente
    (B5); esta comprobación no es una garantía operativa por sí sola."""
    window_id: str
    start_ms: int
    end_ms: int

    def __post_init__(self):
        if not (isinstance(self.window_id, str) and WINDOW_ID.fullmatch(self.window_id)):
            raise SnapshotError(f"ventana reservada con window_id no válido: {self.window_id!r}")
        for name in ("start_ms", "end_ms"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int):
                raise SnapshotError(f"ventana reservada {self.window_id}: {name} debe ser entero (ms)")
        if not self.start_ms < self.end_ms:
            raise SnapshotError(f"ventana reservada {self.window_id}: inicio no anterior al fin")


_SEALING_REQUIREMENT = ("se exige un usuario distinto de root y un sistema de archivos con permisos "
                        "POSIX en el que el modo 0o000 impida la lectura")


def check_sealing_supported(directory: Path) -> None:
    """Sonda previa (QA3R2-08): SealingError si el proceso es root o si un archivo en 0o000
    dentro de `directory` sigue siendo legible. El archivo de sonda se borra siempre."""
    if os.geteuid() == 0:
        raise SealingError(f"el proceso se ejecuta como root: el sellado no es efectivo; {_SEALING_REQUIREMENT}")
    fd, probe = tempfile.mkstemp(prefix=".seal-probe-", dir=directory)
    try:
        os.close(fd)
        os.chmod(probe, MODE_SEALED)
        readable = os.access(probe, os.R_OK)
    finally:
        try:
            os.chmod(probe, stat.S_IRUSR | stat.S_IWUSR)
        finally:
            os.unlink(probe)
    if readable:
        raise SealingError(f"un archivo en 0o000 sigue siendo legible en {directory}; {_SEALING_REQUIREMENT}")


def valid_snapshot_id(snapshot_id) -> bool:
    return isinstance(snapshot_id, str) and SNAPSHOT_ID.fullmatch(snapshot_id) is not None


def enforce_sealing(data_dir: Path, files: dict) -> list[str]:
    """Vuelve a sellar los archivos sellados presentes en `files` (`context`, `oos`, `lockbox`; una
    snapshot de desarrollo no tiene ninguno) si su modo no es 0o000 (aviso SealingWarning) y
    lanza SealingError si el proceso es root o si, tras ello, puede leerlos. Devuelve los avisos
    de re-sellado. No lee su contenido."""
    if os.geteuid() == 0:
        raise SealingError(f"el proceso se ejecuta como root: el sellado no es efectivo; {_SEALING_REQUIREMENT}")
    notes, readable = [], []
    for part in SEALED_FILES:
        if part not in files:
            continue
        path = Path(data_dir) / files[part]["file"]
        if not path.exists():
            continue
        mode = stat.S_IMODE(os.stat(path).st_mode)
        if mode != MODE_SEALED:
            os.chmod(path, MODE_SEALED)
            notes.append(f"{part}: modo {oct(mode)} en lugar de 0o000; se volvió a sellar "
                         "(posible lectura interrumpida)")
        if os.access(path, os.R_OK):
            readable.append(part)
    for note in notes:
        warnings.warn(note, SealingWarning, stacklevel=2)
    if readable:
        raise SealingError(f"el sellado 0o000 no es efectivo para {', '.join(readable)}: el proceso puede "
                           f"leer el archivo; {_SEALING_REQUIREMENT}")
    return notes


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _date_ms(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def parse_d_dev(d_dev) -> int:
    """`D_dev` ("YYYY-MM-DD", medianoche UTC) → ms. Cualquier otro formato es un error."""
    if not isinstance(d_dev, str) or not D_DEV_FORMAT.fullmatch(d_dev):
        raise SnapshotError(f"d_dev no válido: {d_dev!r} (formato YYYY-MM-DD)")
    try:
        return _date_ms(d_dev)
    except ValueError as exc:
        raise SnapshotError(f"d_dev no válido: {d_dev!r}") from exc


def compute_train_end(range_start: int, d_dev_ms: int) -> int:
    """Fin exclusivo de Train (CR-023 §C.1, P1): primeros 5/7 del rango por fecha, en aritmética
    entera y hacia abajo hasta la medianoche UTC; idéntico para 1d, 4h y 1h."""
    span = d_dev_ms - range_start
    if span <= 0:
        raise SnapshotError("rango vacío: d_dev no es posterior al inicio del rango")
    train_end = (range_start + span * TRAIN_VAL_RATIO[0] // sum(TRAIN_VAL_RATIO)) // DAY_MS * DAY_MS
    if not range_start < train_end < d_dev_ms:
        raise SnapshotError(f"corte Train/Validation fuera de rango: {ms_to_iso(train_end)}")
    return train_end


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


def _pack_timestamp(x, what: str) -> bytes:
    if isinstance(x, bool) or not isinstance(x, (int, np.integer)):
        raise SnapshotError(f"digest canónico: {what} debe ser un entero, no {x!r}")
    x = int(x)
    if abs(x) >= 2 ** 53:
        raise SnapshotError(f"digest canónico: {what}={x} fuera de |x| < 2**53")
    return struct.pack(">d", float(x))


def _pack_number(x, what: str) -> bytes:
    try:
        f = float(x)
    except (TypeError, ValueError) as exc:
        raise SnapshotError(f"digest canónico: {what} no numérico: {x!r}") from exc
    return CANONICAL_NAN if math.isnan(f) else struct.pack(">d", f)


def canonical_content_digest(df: pd.DataFrame) -> dict[str, dict]:
    """Digest canónico de contenido (CR-023 §C.6.5), función pura y determinista.

    Por intervalo: {"sha256", "rows", "gaps"} (huecos = filas con `close` NaN). Las filas se
    ordenan por (`interval`, `open_time`) —el orden de entrada no influye—; por fila se serializa
    el intervalo (1 byte de longitud + ASCII) y open_time, close_time, open, high, low, close,
    volume como IEEE-754 binary64 big-endian. Las marcas de tiempo deben ser enteros con
    |x| < 2**53; cualquier NaN se escribe como 0x7FF8000000000000; no hay otra normalización.
    Un (interval, open_time) duplicado o una columna ausente es un error."""
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise SnapshotError(f"digest canónico: faltan columnas {missing}")
    rows = []
    for tup in df[COLUMNS].itertuples(index=False, name=None):
        iv = tup[0]
        if not isinstance(iv, str) or not iv.isascii() or not 0 < len(iv) < 256:
            raise SnapshotError(f"digest canónico: intervalo no válido {iv!r}")
        rows.append(tup)
    rows.sort(key=lambda r: (r[0], int(r[1])))
    hashers: dict[str, "hashlib._Hash"] = {}
    counts: dict[str, list[int]] = {}
    prev = None
    for tup in rows:
        iv = tup[0]
        key = (iv, int(tup[1]))
        if key == prev:
            raise SnapshotError(f"digest canónico: fila duplicada {key}")
        prev = key
        h = hashers.setdefault(iv, hashlib.sha256())
        c = counts.setdefault(iv, [0, 0])
        buf = bytes([len(iv)]) + iv.encode("ascii")
        buf += _pack_timestamp(tup[1], "open_time") + _pack_timestamp(tup[2], "close_time")
        for name, value in zip(_DIGEST_FIELDS[2:], tup[3:]):
            buf += _pack_number(value, name)
        h.update(buf)
        c[0] += 1
        c[1] += int(bool(pd.isna(tup[6])))                     # hueco: `close` NaN
    return {iv: {"sha256": hashers[iv].hexdigest(), "rows": counts[iv][0], "gaps": counts[iv][1]}
            for iv in sorted(hashers)}


@dataclass
class SnapshotResult:
    manifest: dict
    manifest_path: Path
    data_dir: Path
    sealing_warnings: list[str] = field(default_factory=list)


def check_reserved_windows(last_open_by_interval: dict[str, int], reserved_windows: Sequence[ReservedWindow]) -> None:
    """Una snapshot de desarrollo no puede contener datos de una ventana reservada activa: su
    último `open_time` (de cada intervalo) debe ser anterior al inicio de toda ventana activa
    (CR-023 §C.6.5). Comprobación inyectada; la fuente autoritativa de ventanas está pendiente (B5)."""
    for w in reserved_windows:
        for iv, last in last_open_by_interval.items():
            if last >= w.start_ms:
                raise SnapshotError(
                    f"la snapshot de desarrollo ({iv}, último open_time {ms_to_iso(last)}) alcanza la ventana "
                    f"reservada {w.window_id} (inicio {ms_to_iso(w.start_ms)})")


def build_snapshot(client: BinancePublicClient, snapshot_id: str, data_root: Path, manifest_dir: Path, *,
                   d_dev: str, reserved_windows: Sequence[ReservedWindow], start_date: str = START_DATE,
                   now=lambda: datetime.now(timezone.utc)) -> SnapshotResult:
    """Construye la snapshot de DESARROLLO [range_start, d_dev) (CR-023 §C.1). `reserved_windows`
    son las ventanas ACTIVAS entregadas por quien llama (interfaz inyectada; fuente autoritativa
    pendiente en B5, no es control operativo). No construye snapshots de evaluación."""
    if not valid_snapshot_id(snapshot_id):
        raise SnapshotError(f"identificador de snapshot no válido: {snapshot_id!r}")
    d_dev_ms = parse_d_dev(d_dev)
    windows = list(reserved_windows)
    if not all(isinstance(w, ReservedWindow) for w in windows):
        raise SnapshotError("reserved_windows debe contener solo ReservedWindow")
    data_root, manifest_dir = Path(data_root), Path(manifest_dir)
    data_dir = data_root / snapshot_id
    manifest_path = manifest_dir / f"{snapshot_id}.json"
    if manifest_path.exists():
        raise SnapshotError(f"la snapshot {snapshot_id} ya existe: una snapshot no se reescribe")
    # QA3R2-08: sonda de sellado antes de descargar y antes de apartar un huérfano
    created_root = not data_root.exists()
    data_root.mkdir(parents=True, exist_ok=True)
    try:
        check_sealing_supported(data_root)
        prepared = _download_and_prepare(client, start_date, d_dev_ms, windows, now)
    except BaseException:
        if created_root:
            try:
                data_root.rmdir()
            except OSError:
                pass
        raise
    (downloaded_at, server_ms, range_start, first_open, frames, train_end, digests) = prepared

    data_root.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    quarantined = None
    if data_dir.exists():                 # sin manifiesto: construcción interrumpida (QA3R2-02)
        quarantined = f".incomplete-{snapshot_id}-{now().strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}"
        os.rename(data_dir, data_root / quarantined)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f".tmp-{snapshot_id}-", dir=data_root))
    tmp_manifest = manifest_path.with_suffix(".json.tmp")
    renamed = False
    try:
        out = pd.concat([frames[iv] for iv in SNAPSHOT_INTERVALS], ignore_index=True)
        stats = {}
        for iv in SNAPSHOT_INTERVALS:
            sel = frames[iv]
            stats[iv] = {"rows": int(len(sel)), "gaps": int(sel["close"].isna().sum()),
                         "first_open_time_utc": ms_to_iso(int(sel["open_time"].min())),
                         "last_open_time_utc": ms_to_iso(int(sel["open_time"].max()))}
        path = tmp_dir / "train_val.parquet"
        pq.write_table(pyarrow.Table.from_pandas(out, preserve_index=False), path)
        files = {"train_val": {"file": "train_val.parquet", "sha256": sha256_file(path), "rows": int(len(out)),
                               "per_interval": stats, "canonical_digest": digests}}
        os.chmod(path, MODE_READONLY)
        sealing_notes = enforce_sealing(tmp_dir, files)       # QA3R2-08: antes de confirmar
        manifest = _manifest(client, snapshot_id, downloaded_at, server_ms, start_date, range_start, d_dev, d_dev_ms,
                             first_open, train_end, files, quarantined, windows,
                             max(int(frames[iv]["open_time"].max()) for iv in SNAPSHOT_INTERVALS))
        with open(tmp_manifest, "w") as fh:
            fh.write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp_dir, data_dir)
        renamed = True
        os.replace(tmp_manifest, manifest_path)          # confirmación (QA3R2-02)
    except BaseException:
        _remove_tree(data_dir if renamed else tmp_dir)
        tmp_manifest.unlink(missing_ok=True)
        raise
    return SnapshotResult(manifest, manifest_path, data_dir, sealing_notes)


def _download_and_prepare(client, start_date, d_dev_ms, windows, now):
    """Descarga, rejillas, corte 5:2, digests y comprobación de ventanas reservadas; no escribe nada."""
    downloaded_at = now().strftime("%Y-%m-%dT%H:%M:%SZ")
    server_ms = client.server_time_ms()
    if d_dev_ms > server_ms:
        raise SnapshotError(f"los datos no llegan a d_dev ({ms_to_iso(d_dev_ms)}): hora del servidor "
                            f"{ms_to_iso(server_ms)}")
    start_ms = _date_ms(start_date)
    if d_dev_ms <= start_ms:
        raise SnapshotError(f"d_dev ({ms_to_iso(d_dev_ms)}) no es posterior al inicio del rango")
    candles: dict[str, list[Candle]] = {}
    for iv in SNAPSHOT_INTERVALS:
        end = last_closed_open_time(iv, d_dev_ms)             # última vela cerrada antes de D_dev
        try:
            cs = closed_only(client.klines_range(iv, start_ms, end, require_end=True), server_ms)
        except Exception as exc:
            raise SnapshotError(f"descarga de {iv} fallida o incompleta: {exc}") from exc
        if not cs:
            raise SnapshotError(f"sin datos para {iv}")
        candles[iv] = cs
    range_start = min(cs[0].open_time for cs in candles.values()) // DAY_MS * DAY_MS
    if not range_start < d_dev_ms:
        raise SnapshotError("d_dev no es posterior al inicio del rango")
    first_open, frames = {}, {}
    for iv in SNAPSHOT_INTERVALS:
        first = candles[iv][0].open_time
        if first >= range_start + DAY_MS:
            raise SnapshotError(f"{iv}: la primera vela ({ms_to_iso(first)}) no cae en el primer día del rango")
        if candles[iv][-1].open_time < d_dev_ms - interval_ms(iv):
            raise SnapshotError(f"{iv}: los datos no llegan a d_dev ({ms_to_iso(d_dev_ms)})")
        first_open[iv] = first
        frames[iv] = to_grid_frame(iv, [c for c in candles[iv] if c.open_time < d_dev_ms], first, d_dev_ms)
    train_end = compute_train_end(range_start, d_dev_ms)
    check_reserved_windows({iv: int(frames[iv]["open_time"].max()) for iv in SNAPSHOT_INTERVALS}, windows)
    digests = canonical_content_digest(pd.concat([frames[iv] for iv in SNAPSHOT_INTERVALS], ignore_index=True))
    return downloaded_at, server_ms, range_start, first_open, frames, train_end, digests


def _remove_tree(directory: Path) -> None:
    for p in directory.glob("*"):
        os.chmod(p, stat.S_IWUSR | stat.S_IRUSR)
    shutil.rmtree(directory, ignore_errors=True)


def _manifest(client, snapshot_id, downloaded_at, server_ms, start_date, range_start, d_dev, d_dev_ms,
              first_open, train_end, files, quarantined, windows, last_open_ms) -> dict:
    per = files["train_val"]["per_interval"]
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "kind": KIND_DEVELOPMENT,
        "snapshot_id": snapshot_id,
        "window_id": None,
        "d_dev": d_dev,
        "d_dev_ms": d_dev_ms,
        "downloaded_at_utc": downloaded_at,
        "binance_server_time_utc": ms_to_iso(server_ms),
        "source": {"base_url": client.base_url, "endpoint": "GET /api/v3/klines", "symbol": SYMBOL,
                   "intervals": list(SNAPSHOT_INTERVALS), "limit": KLINES_LIMIT, "start_date": start_date,
                   "only_closed_candles": True, "require_complete_download": True},
        "range": {"start_ms": range_start, "start_utc": ms_to_iso(range_start),
                  "end_exclusive_utc": ms_to_iso(d_dev_ms),
                  "last_open_time_ms": last_open_ms},
        "listing_start": {iv: {"first_open_time_utc": ms_to_iso(first_open[iv]),
                               "rows_before_first_candle_excluded": (first_open[iv] - range_start) // interval_ms(iv)}
                          for iv in SNAPSHOT_INTERVALS},
        "split": {"train_validation": f"{TRAIN_VAL_RATIO[0]}:{TRAIN_VAL_RATIO[1]}",
                  "method": "cronológico por fecha, aritmética entera; corte idéntico para 1d, 4h y 1h"},
        "cuts_utc": {"train_end_exclusive": ms_to_iso(train_end)},
        "cuts_ms": {"train_end": train_end},
        "gaps_total": {iv: per[iv]["gaps"] for iv in SNAPSHOT_INTERVALS},
        "files": files,
        "canonical_digest_algorithm": CANONICAL_DIGEST_ALGORITHM,
        "file_modes": {"train_val": "0o444"},
        "reserved_windows_checked": [w.window_id for w in windows],
        "writer": {"python": platform.python_version(), "pandas": pd.__version__, "pyarrow": pyarrow.__version__},
        "incomplete_build_quarantined": quarantined,
    }


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _fail(msg: str):
    raise SnapshotError(f"manifiesto no válido: {msg}")


def _check_digest(where: str, d) -> None:
    if not isinstance(d, dict) or set(d) != set(SNAPSHOT_INTERVALS):
        _fail(f"{where}: canonical_digest debe cubrir exactamente {list(SNAPSHOT_INTERVALS)}")
    for iv, e in d.items():
        if not (isinstance(e, dict) and set(e) == {"sha256", "rows", "gaps"} and isinstance(e["sha256"], str)
                and SHA256_HEX.fullmatch(e["sha256"]) and _is_int(e["rows"]) and e["rows"] > 0
                and _is_int(e["gaps"]) and 0 <= e["gaps"] <= e["rows"]):
            _fail(f"{where}: digest canónico mal formado para {iv}")


def _check_file(name: str, info) -> None:
    if not isinstance(info, dict):
        _fail(f"files.{name} mal formado")
    if info.get("file") != f"{name}.parquet":
        _fail(f"files.{name}.file debe ser {name}.parquet")
    if not (isinstance(info.get("sha256"), str) and SHA256_HEX.fullmatch(info["sha256"])):
        _fail(f"files.{name}.sha256 no válido")
    if not (_is_int(info.get("rows")) and info["rows"] > 0):
        _fail(f"files.{name}.rows no válido")
    _check_digest(f"files.{name}", info.get("canonical_digest"))


def validate_manifest(m) -> dict:
    """Valida el esquema 2.0.0 por `kind` (CR-023 §C.1, §C.6.2). Un manifiesto sin `kind`, con
    `kind` desconocido, heredado o mal formado se rechaza (Fail-Closed). Solo valida estructura:
    no lee archivos. Para `evaluation` no hay constructor todavía (B6)."""
    if not isinstance(m, dict):
        _fail("no es un objeto")
    if not valid_snapshot_id(m.get("snapshot_id")):
        raise SnapshotError(f"manifiesto con snapshot_id no válido: {m.get('snapshot_id')!r}")
    kind = m.get("kind")
    if kind not in (KIND_DEVELOPMENT, KIND_EVALUATION):
        _fail(f"kind ausente o desconocido ({kind!r}); los manifiestos heredados sin kind se rechazan")
    if m.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        _fail(f"schema_version {m.get('schema_version')!r} ≠ {MANIFEST_SCHEMA_VERSION}")
    files = m.get("files")
    if not isinstance(files, dict):
        _fail("files ausente")
    d_dev = m.get("d_dev")
    try:
        d_dev_ms = parse_d_dev(d_dev)
    except SnapshotError:
        _fail(f"d_dev no válido: {d_dev!r}")
    if m.get("d_dev_ms") != d_dev_ms:
        _fail("d_dev_ms no coincide con d_dev")
    if not (isinstance(m.get("canonical_digest_algorithm"), str) and m["canonical_digest_algorithm"]):
        _fail("canonical_digest_algorithm ausente")
    rng = m.get("range")
    if not (isinstance(rng, dict) and _is_int(rng.get("last_open_time_ms"))):
        _fail("range.last_open_time_ms ausente")
    if kind == KIND_DEVELOPMENT:
        if set(files) != {"train_val"}:
            _fail(f"una snapshot de desarrollo solo contiene train_val, no {sorted(files)}")
        if m.get("window_id") is not None:
            _fail("window_id debe ser null en una snapshot de desarrollo")
        _check_file("train_val", files["train_val"])
        cuts = m.get("cuts_ms")
        if not (isinstance(cuts, dict) and _is_int(cuts.get("train_end")) and cuts["train_end"] < d_dev_ms
                and _is_int(rng.get("start_ms")) and rng["start_ms"] < cuts["train_end"]):
            _fail("cuts_ms.train_end ausente o fuera de [range.start_ms, d_dev)")
        if m.get("file_modes") != {"train_val": "0o444"}:
            _fail("file_modes de desarrollo debe ser {train_val: 0o444}")
        return m
    wid = m.get("window_id")
    if not (isinstance(wid, str) and WINDOW_ID.fullmatch(wid)):
        _fail(f"window_id no válido: {wid!r} (EXP-NNNN/OOS|LOCKBOX)")
    part = wid.rsplit("/", 1)[1].lower()
    if set(files) != {"context", part}:
        _fail(f"una snapshot de evaluación {wid} contiene exactamente context y {part}, no {sorted(files)}")
    for name in ("context", part):
        _check_file(name, files[name])
    win = m.get("window")
    if not (isinstance(win, dict) and _is_int(win.get("start_ms")) and _is_int(win.get("end_exclusive_ms"))
            and d_dev_ms <= win["start_ms"] < win["end_exclusive_ms"]):
        _fail("window.start_ms/end_exclusive_ms ausentes o fuera de orden (d_dev ≤ inicio < fin)")
    if m.get("context_start_ms") != d_dev_ms:
        _fail("el primer open_time del context debe ser D_dev")
    ref = m.get("development_snapshot")
    if not (isinstance(ref, dict) and valid_snapshot_id(ref.get("snapshot_id"))
            and isinstance(ref.get("train_val_sha256"), str) and SHA256_HEX.fullmatch(ref["train_val_sha256"])):
        _fail("development_snapshot debe citar snapshot_id y train_val_sha256")
    if m.get("file_modes") != {"context": "0o000", part: "0o000"}:
        _fail("file_modes de evaluación debe ser 0o000 para context y la partición")
    return m


def load_manifest(manifest_path: Path) -> dict:
    return validate_manifest(json.loads(Path(manifest_path).read_text()))


def verify_snapshot(manifest_path: Path, data_root: Path) -> dict[str, str]:
    """Verificación por `kind` (TC-ML-015).

    - development: comprueba el sellado (sin archivos sellados) y recalcula el SHA-256 de
      `train_val`; falla si difiere del manifiesto.
    - evaluation: solo comprueba el sellado de `context` y la partición (SealingError si no es
      efectivo); NO lee ni hashea archivos sellados, porque hashearlos es leerlos. Su SHA-256 se
      verifica dentro de `PartitionLoader.load_final`, con autorización y consumo (QA3-06)."""
    m = load_manifest(manifest_path)
    data_dir = Path(data_root) / m["snapshot_id"]
    enforce_sealing(data_dir, m["files"])
    if m["kind"] == KIND_EVALUATION:
        return {}
    info = m["files"]["train_val"]
    actual = sha256_file(data_dir / info["file"])
    if actual != info["sha256"]:
        raise SnapshotError(f"train_val: SHA-256 {actual} ≠ manifiesto {info['sha256']}")
    return {"train_val": actual}
