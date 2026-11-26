"""Snapshot de evaluación (ET-4) y fuente autoritativa de ventanas reservadas (CR-023 §C.6, §C.7, §C.9; bloque B5).

- `build_evaluation_snapshot`: construye la snapshot `evaluation` de una ventana `EXP-NNNN/OOS|LOCKBOX`
  tras el cierre de la ventana. Exige `--confirm`, las comprobaciones de ET-4 (V1, V2, V3, V4-pre, V8, de
  `independence.stage_checks`) y, para el LOCKBOX, la continuidad del contexto (C.6.5) contra el manifiesto
  versionado de la OOS (no abre `oos.parquet`, no autoriza, no calcula resultados). Digests canónicos en
  memoria antes de sellar; mismo rollback y sellado que `build_snapshot` (nada queda en disco si falla).
- `reserved_windows_source`: deriva del registro y del almacén las ventanas ACTIVAS (reservadas, no
  consumidas) de todo preregistro confirmatorio; `build_snapshot(..., reserved_windows_source=...)` la
  suma a las ventanas inyectadas. Fail-Closed: un preregistro confirmatorio ilegible bloquea la
  construcción. No hay mecanismo de liberación (C.7.3): toda ventana no consumida se considera activa.
No se lee ningún dato sellado; `_FINAL_ACCESS_BLOCKED_UNTIL_B6` sigue vigente en `partitions.py`.
"""
from __future__ import annotations

import json
import os
import platform
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow
import pyarrow.parquet as pq

from swingpilot.market_data import BinancePublicClient, interval_ms, last_closed_open_time
from swingpilot.market_data.binance_public import KLINES_LIMIT
from swingpilot.market_data.candles import SYMBOL, closed_only, ms_to_iso

from . import boundary as B
from . import independence as I
from . import snapshot as S
from .snapshot import SnapshotError


def reserved_windows_source(registry, store) -> Callable[[], list]:
    """Fuente autoritativa de ventanas activas. Devuelve un invocable sin argumentos → [ReservedWindow]."""
    def source() -> list:
        try:
            records, exps = registry.records(), registry.experiments()
            out = []
            for eid, exp in exps.items():
                pre = [h for h in exp["history"] if h.get("kind") == "TRANSITION" and h.get("to") == "PREREGISTERED"]
                if not pre or (pre[0].get("evidence") or {}).get("independence_class") != B.CONFIRMATORY:
                    continue
                sha = pre[0]["evidence"]["preregistration_sha256"]
                content = store.verify_cited(eid, sha)
                released = I.released_windows(registry.decisions_dir, eid, sha)    # C.7.3: dato de desarrollo
                ib = content.get("independence_boundary")
                if B.boundary_class(ib) != B.CONFIRMATORY or B.boundary_error(ib):
                    raise SnapshotError(f"{eid}: independence_boundary confirmatoria no válida")
                for wid, (start, end) in B.windows(ib, eid).items():
                    part = wid.rsplit("/", 1)[1].lower()
                    consumed = any(r.get("kind") == "PARTITION_CONSUMED" and r.get("experiment_id") == eid
                                   and r.get("partition") == part for r in records)
                    if not consumed and wid not in released:
                        out.append(S.ReservedWindow(wid, B.to_ms(start), B.to_ms(end)))
            return out
        except SnapshotError:
            raise
        except I._Fail as f:
            raise SnapshotError(f"fuente de ventanas reservadas no verificable (Fail-Closed): {f.why}") from f
        except Exception as exc:
            raise SnapshotError(f"fuente de ventanas reservadas no verificable (Fail-Closed): {exc!r}") from exc
    return source


def _download(client, iv, d_dev_ms, end_ms, server_ms) -> pd.DataFrame:
    last = last_closed_open_time(iv, end_ms)
    try:
        cs = closed_only(client.klines_range(iv, d_dev_ms, last, require_end=True), server_ms)
    except Exception as exc:
        raise SnapshotError(f"descarga de {iv} fallida o incompleta: {exc}") from exc
    if not cs or cs[-1].open_time < end_ms - interval_ms(iv):
        raise SnapshotError(f"{iv}: los datos no llegan al fin de la ventana ({ms_to_iso(end_ms)})")
    return S.to_grid_frame(iv, [c for c in cs if d_dev_ms <= c.open_time < end_ms], d_dev_ms, end_ms)


def _stats(df) -> dict:
    return {iv: {"rows": int(len(g)), "gaps": int(g["close"].isna().sum()),
                 "first_open_time_utc": ms_to_iso(int(g["open_time"].min())),
                 "last_open_time_utc": ms_to_iso(int(g["open_time"].max()))}
            for iv, g in df.groupby("interval", sort=True)}


def _preflight(registry, store, eid, window_id, manifest_dir, data_root, decisions_dir):
    """ET-4 antes de descargar: V1, V2, V3, V4-pre, V8, reutilización de la clase y la snapshot de desarrollo."""
    wins = None
    try:
        ctx = I._context(registry, store, eid)
        wins = B.windows(ctx["ib"], eid)
    except I._Fail as f:
        raise SnapshotError(f"ET-4 bloqueada: {f.why}") from f
    if window_id not in wins:
        raise SnapshotError(f"{window_id} no es una ventana de {eid}")
    part = window_id.rsplit("/", 1)[1].lower()
    checks = I.stage_checks(registry, store, eid, "ET-4", decisions_dir=decisions_dir,
                            manifest={"window_id": window_id, "snapshot_id": None})
    bad = {k: v for k, v in checks.items() if v[0] != I.OK}
    if bad:
        raise SnapshotError(f"ET-4 bloqueada por las comprobaciones {bad}")
    # V4-pre sobre la ventana y no solo sobre el id de la nueva snapshot: ninguna consumición previa.
    for r in registry.records():
        if r.get("kind") == "PARTITION_CONSUMED" and r.get("partition") == part and (
                part == "lockbox" or r.get("experiment_id") == eid):
            raise SnapshotError(f"V4-pre: {window_id} ya tiene un PARTITION_CONSUMED (una ventana consumida no se reconstruye)")
    snap = ctx["content"]["snapshot"]
    dev_path = Path(manifest_dir) / f"{snap['snapshot_id']}.json"
    try:
        dev = S.load_manifest(dev_path)
        S.verify_snapshot(dev_path, data_root)
    except Exception as exc:
        raise SnapshotError(f"snapshot de desarrollo no verificable: {exc}") from exc
    if dev["kind"] != S.KIND_DEVELOPMENT or dev["files"]["train_val"]["sha256"] != snap["train_val_sha256"] \
            or dev["d_dev"] != snap["d_dev"]:
        raise SnapshotError("la snapshot de desarrollo no es la del preregistro (hash, kind o D_dev)")
    return ctx, wins, dev


def _oos_manifest(ctx, eid, manifest_dir):
    found = []
    for p in sorted(Path(manifest_dir).glob("*.json")):
        try:
            m = json.loads(p.read_text())
        except Exception as exc:
            raise SnapshotError(f"manifiesto ilegible {p.name}: {exc!r}") from exc
        if isinstance(m, dict) and m.get("kind") == S.KIND_EVALUATION and m.get("window_id") == f"{eid}/OOS":
            found.append(m)
    if len(found) != 1:
        raise SnapshotError(f"continuidad C.6.5: se exige exactamente un manifiesto de {eid}/OOS (hay {len(found)})")
    try:
        I._check_manifest(ctx, eid, found[0], f"{eid}/OOS")
    except I._Fail as f:
        raise SnapshotError(f"continuidad C.6.5: manifiesto de la OOS no válido: {f.why}") from f
    return found[0]


DISCREPANCY_DIR = "lockbox_discrepancies"


def _discrepancies(manifest_dir, eid) -> list[Path]:
    return sorted((Path(manifest_dir) / DISCREPANCY_DIR).glob(f"{eid}-*.json"))


def _lockbox_retry_gate(eid, manifest_dir, ddir) -> None:
    """C.6.5 (disposición del propietario): sin disposición INCONCLUSIVE; toda discrepancia previa debe
    estar documentada (`REINTENTO` con el SHA-256 del archivo de evidencia) antes de repetir la descarga."""
    try:
        if I.owner_lines(ddir, "DISPOSICION", I._DISPOSICION, eid):
            raise SnapshotError(f"{eid}/LOCKBOX: el propietario dispuso INCONCLUSIVE; no se vuelve a construir")
        documented = {h for _, h in I.owner_lines(ddir, "REINTENTO", I._REINTENTO, eid)}
    except I._Fail as f:
        raise SnapshotError(f"ET-4 bloqueada: {f.why}") from f
    for ev in _discrepancies(manifest_dir, eid):
        if S.sha256_file(ev) not in documented:
            raise SnapshotError(f"discrepancia sin documentar ({ev.name}): registrar en docs/decisions "
                                f"`AUTORIZA: REINTENTO {eid}/LOCKBOX EVIDENCIA={S.sha256_file(ev)}` antes de reintentar")


def _record_discrepancy(manifest_dir, eid, snapshot_id, name, expected, actual) -> Path:
    """Evidencia inmutable (modo 'x', fsync) de la discrepancia; no contiene datos de mercado."""
    d = Path(manifest_dir) / DISCREPANCY_DIR
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = d / f"{eid}-{stamp}-{os.getpid()}.json"             # el contenido incluye `recorded_at`: cada intento es único
    with open(path, "x") as fh:
        fh.write(json.dumps({"experiment_id": eid, "window_id": f"{eid}/LOCKBOX", "attempted_snapshot_id": snapshot_id, "recorded_at": stamp,
                             "mismatch": name, "expected_oos_manifest_digest": expected, "lockbox_context_digest": actual,
                             "disposition": "pendiente: documentar en docs/decisions; si persiste, INCONCLUSIVE"},
                            indent=2) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return path


def _check_continuity(oos, context_df, oos_start_ms, *, manifest_dir=None, eid=None, snapshot_id=None) -> None:
    """Contexto del LOCKBOX = contexto de la OOS en [D_dev, B) + periodo de la OOS en [B, B + L_oos)."""
    parts = (("context", context_df[context_df["open_time"] < oos_start_ms], oos["files"]["context"]),
             ("oos", context_df[context_df["open_time"] >= oos_start_ms], oos["files"]["oos"]))
    for name, df, info in parts:
        actual = S.canonical_content_digest(df)
        if actual != info["canonical_digest"]:
            ev = _record_discrepancy(manifest_dir, eid, snapshot_id, name, info["canonical_digest"], actual)
            raise SnapshotError(f"continuidad C.6.5: el contexto del LOCKBOX no reproduce el digest/filas/huecos "
                                f"de {name} de la OOS; construcción abortada, LOCKBOX bloqueado; evidencia "
                                f"{ev.name}: documentar en docs/decisions antes de reintentar")


def build_evaluation_snapshot(client: BinancePublicClient, snapshot_id: str, data_root: Path, manifest_dir: Path, *,
                              registry, store, experiment_id: str, window_id: str, confirm: bool,
                              decisions_dir=None, now=lambda: datetime.now(timezone.utc)) -> S.SnapshotResult:
    """ET-4 (CR-023 §C.6.1–C.6.2). Sin `confirm=True` (`--confirm` del propietario), no hace nada."""
    if confirm is not True:
        raise SnapshotError("ET-4 exige la confirmación del propietario (--confirm)")
    if not S.valid_snapshot_id(snapshot_id):
        raise SnapshotError(f"identificador de snapshot no válido: {snapshot_id!r}")
    data_root, manifest_dir = Path(data_root), Path(manifest_dir)
    data_dir, manifest_path = data_root / snapshot_id, manifest_dir / f"{snapshot_id}.json"
    if manifest_path.exists():
        raise SnapshotError(f"la snapshot {snapshot_id} ya existe: una snapshot no se reescribe")
    ddir = decisions_dir if decisions_dir is not None else getattr(registry, "decisions_dir", None)
    ctx, wins, dev = _preflight(registry, store, experiment_id, window_id, manifest_dir, data_root, ddir)
    part = window_id.rsplit("/", 1)[1].lower()
    start, end = wins[window_id]
    start_ms, end_ms, d_dev_ms = B.to_ms(start), B.to_ms(end), dev["d_dev_ms"]
    if not d_dev_ms < start_ms:
        raise SnapshotError("D_dev no es anterior al inicio de la ventana")
    if part == "lockbox":
        _lockbox_retry_gate(experiment_id, manifest_dir, ddir)
    oos = _oos_manifest(ctx, experiment_id, manifest_dir) if part == "lockbox" else None

    created_root = not data_root.exists()
    data_root.mkdir(parents=True, exist_ok=True)
    try:
        S.check_sealing_supported(data_root)
        downloaded_at = now().strftime("%Y-%m-%dT%H:%M:%SZ")
        server_ms = client.server_time_ms()
        if server_ms < end_ms:                                  # ventana cerrada según la hora del servidor
            raise SnapshotError(f"la ventana {window_id} no ha cerrado: fin {ms_to_iso(end_ms)}, "
                                f"servidor {ms_to_iso(server_ms)}")
        full = pd.concat([_download(client, iv, d_dev_ms, end_ms, server_ms) for iv in S.SNAPSHOT_INTERVALS],
                         ignore_index=True)
        context_df, window_df = full[full["open_time"] < start_ms], full[full["open_time"] >= start_ms]
        digests = {"context": S.canonical_content_digest(context_df), part: S.canonical_content_digest(window_df)}
        if oos is not None:
            _check_continuity(oos, context_df, B.to_ms(wins[f"{experiment_id}/OOS"][0]),
                              manifest_dir=manifest_dir, eid=experiment_id, snapshot_id=snapshot_id)
    except BaseException:
        if created_root:
            try:
                data_root.rmdir()
            except OSError:
                pass
        raise

    manifest_dir.mkdir(parents=True, exist_ok=True)
    quarantined = None
    if data_dir.exists():
        quarantined = f".incomplete-{snapshot_id}-{now().strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}"
        os.rename(data_dir, data_root / quarantined)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f".tmp-{snapshot_id}-", dir=data_root))
    tmp_manifest = manifest_path.with_suffix(".json.tmp")
    renamed = False
    try:
        files = {}
        for name, df in (("context", context_df), (part, window_df)):
            path = tmp_dir / f"{name}.parquet"
            pq.write_table(pyarrow.Table.from_pandas(df.reset_index(drop=True), preserve_index=False), path)
            files[name] = {"file": f"{name}.parquet", "sha256": S.sha256_file(path), "rows": int(len(df)),
                           "per_interval": _stats(df), "canonical_digest": digests[name]}
            os.chmod(path, S.MODE_SEALED)
        notes = S.enforce_sealing(tmp_dir, files)
        manifest = {
            "schema_version": S.MANIFEST_SCHEMA_VERSION, "kind": S.KIND_EVALUATION, "snapshot_id": snapshot_id,
            "window_id": window_id, "d_dev": dev["d_dev"], "d_dev_ms": d_dev_ms,
            "downloaded_at_utc": downloaded_at, "binance_server_time_utc": ms_to_iso(server_ms),
            "source": {"base_url": client.base_url, "endpoint": "GET /api/v3/klines", "symbol": SYMBOL,
                       "intervals": list(S.SNAPSHOT_INTERVALS), "limit": KLINES_LIMIT,
                       "only_closed_candles": True, "require_complete_download": True},
            "window": {"start_ms": start_ms, "end_exclusive_ms": end_ms, "start_utc": ms_to_iso(start_ms),
                       "end_exclusive_utc": ms_to_iso(end_ms)},
            "context_start_ms": d_dev_ms,
            "range": {"start_ms": d_dev_ms, "last_open_time_ms": int(window_df["open_time"].max())},
            "development_snapshot": {"snapshot_id": dev["snapshot_id"],
                                     "train_val_sha256": dev["files"]["train_val"]["sha256"]},
            "files": files, "canonical_digest_algorithm": S.CANONICAL_DIGEST_ALGORITHM,
            "file_modes": {"context": "0o000", part: "0o000"},
            "lockbox_continuity": ({"oos_snapshot_id": oos["snapshot_id"], "verified": True} if oos else None),
            "writer": {"python": platform.python_version(), "pandas": pd.__version__, "pyarrow": pyarrow.__version__},
            "incomplete_build_quarantined": quarantined,
        }
        S.validate_manifest(manifest)
        try:
            I._check_manifest(ctx, experiment_id, manifest, window_id)      # V5 en memoria, antes de confirmar
        except I._Fail as f:
            raise SnapshotError(f"V5: {f.why}") from f
        with open(tmp_manifest, "w") as fh:
            fh.write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp_dir, data_dir)
        renamed = True
        os.replace(tmp_manifest, manifest_path)
    except BaseException:
        S._remove_tree(data_dir if renamed else tmp_dir)
        tmp_manifest.unlink(missing_ok=True)
        raise
    return S.SnapshotResult(manifest, manifest_path, data_dir, notes)
