"""Acceso controlado a las particiones de la snapshot (FEAT-015/017; REQ-G-101, REQ-G-109;
TC-ML-001, TC-ML-007, TC-ML-012, TC-ML-016, TC-ML-019).

- `train_val` (tras verificar su SHA-256): la única vía pública es
  `load_train_val_for_configuration`, que exige el inicio de evaluación registrado (CR-020; A2).
- `oos` y `lockbox` (archivos sin permisos, 0o000) solo con una `FinalEvaluationGrant`:
  experimento del propio registro (no un antecedente, QA3-03) en OOS_EVALUATION; autorización
  del propietario citando una decisión de docs/decisions con la línea exacta
  `AUTORIZA: <EXP-NNNN> <partición> <snapshot>` (QA3-04, QA3R2-04; sin búsqueda por
  subcadena); partición no consumida. El consumo se registra en el
  registro de experimentos (versionado) ANTES de leer, y también en el registro de accesos
  (QA3-06).
- La comprobación de «no consumida» y su registro son atómicos entre procesos
  (`ExperimentRegistry.claim_partition`, QA3R2-03): de dos cargadores concurrentes, solo uno
  consume y lee; el otro queda denegado y anotado.
- Una lectura fallida tras el registro (p. ej. SHA-256 distinto) deja la partición
  CONSUMIDA, a propósito: el dato pudo quedar expuesto y no se permite un segundo intento. El
  fallo se anota en el registro de accesos (QA3R2-03).
- El control es en proceso: impide el uso accidental o no trazable desde el código; no
  sustituye permisos del sistema operativo frente a un usuario con privilegios.
- Sellado (QA3R2-08): el cargador no se construye si OOS/LOCKBOX son legibles por el proceso
  (root o sistema de archivos sin permisos POSIX), tampoco para `train_val`; `load_final` lo
  vuelve a comprobar ANTES de registrar el consumo, de modo que un bloqueo nunca consume la
  partición.
- DEC-018: en IMPL-3 no se evalúan OOS ni LOCKBOX; ninguna autorización real se emite.
- CR-020 (§C.3.2) y A2 (opción B del propietario): `load_train_val_for_configuration` solo
  entrega Train+Val si el par (experimento, configuración) está en la evidencia VALIDADA del
  registro (`accounting()["pairs"]`). Registro ausente, ilegible, corrupto, mal formado o
  incoherente → denegado, anotado y sin leer datos (Fail-Closed). La lectura sin configuración
  es privada (`_load_train_val_for_inspection`): solo para comprobar la integridad de la snapshot
  (FEAT-015); una guarda estática impide usarla fuera de este módulo en `src/` y `scripts/`.
- Límite de arquitectura: es un control de las vías de acceso de la aplicación, no de seguridad
  del sistema de archivos. `train_val.parquet` no está sellado (FEAT-015) y cualquier proceso
  puede leerlo directamente.
"""
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import hashlib

import pandas as pd
import pyarrow
import pyarrow.parquet as pq

from .snapshot import MODE_SEALED, SEALED, SealingError, enforce_sealing, load_manifest, sha256_file


class PartitionAccessError(PermissionError):
    pass


@dataclass(frozen=True)
class FinalEvaluationGrant:
    experiment_id: str
    partition: str             # "oos" | "lockbox"
    snapshot_id: str
    approved_by: str           # debe ser el propietario
    decision_ref: str          # nombre del documento de decisión en docs/decisions


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PartitionLoader:
    def __init__(self, manifest_path: Path, data_root: Path, access_log: Path, *, registry=None,
                 owner: str = "propietario"):
        self.manifest = load_manifest(manifest_path)
        self.data_dir = Path(data_root) / self.manifest["snapshot_id"]
        self.access_log = Path(access_log)
        self.registry = registry
        self.owner = owner
        enforce_sealing(self.data_dir, self.manifest["files"])     # QA3R2-08: SealingError bloquea

    def _log(self, partition: str, allowed: bool, reason: str, experiment_id: str | None) -> None:
        self.access_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.access_log, "a") as fh:
            fh.write(json.dumps({"at_utc": _now(), "snapshot_id": self.manifest["snapshot_id"],
                                 "partition": partition, "allowed": allowed, "reason": reason,
                                 "experiment_id": experiment_id}, ensure_ascii=False) + "\n")

    def access_history(self) -> list[dict]:
        if not self.access_log.exists():
            return []
        return [json.loads(line) for line in self.access_log.read_text().splitlines() if line.strip()]

    def _consumed(self, partition: str, experiment_id: str) -> bool:
        sid = self.manifest["snapshot_id"]
        if self.registry is not None and self.registry.is_consumed(sid, partition, experiment_id):
            return True
        for r in self.access_history():   # defensa adicional; la fuente de verdad es el registro
            if r["allowed"] and r["partition"] == partition and r["snapshot_id"] == sid:
                if partition == "lockbox" or r["experiment_id"] == experiment_id:
                    return True
        return False

    def _read(self, partition: str) -> pd.DataFrame:
        info = self.manifest["files"][partition]
        path = self.data_dir / info["file"]
        sealed = partition in SEALED
        if sealed:
            # QA3R2-08: se abre y se vuelve a sellar de inmediato; hash y parseo usan el
            # descriptor ya abierto, así un SIGKILL durante la lectura no deja el archivo en 0o400.
            os.chmod(path, stat.S_IRUSR)
            try:
                fh = open(path, "rb")
            finally:
                os.chmod(path, MODE_SEALED)
            with fh:
                data = fh.read()
            if hashlib.sha256(data).hexdigest() != info["sha256"]:
                raise PartitionAccessError(f"{partition}: SHA-256 no coincide con el manifiesto")
            return pq.read_table(pyarrow.BufferReader(data)).to_pandas()
        if sha256_file(path) != info["sha256"]:
            raise PartitionAccessError(f"{partition}: SHA-256 no coincide con el manifiesto")
        return pq.read_table(path).to_pandas()

    def _load_train_val_for_inspection(self, interval: str | None = None) -> pd.DataFrame:
        """Uso interno: inspección de la integridad de la snapshot (FEAT-015). No es una vía de
        evaluación; las evaluaciones usan `load_train_val_for_configuration` (CR-020, A2)."""
        self._log("train_val", True, "desarrollo", None)
        df = self._read("train_val")
        return df[df["interval"] == interval].reset_index(drop=True) if interval else df

    def load_train_val_for_configuration(self, experiment_id: str, config_id: str,
                                         interval: str | None = None) -> pd.DataFrame:
        """Train+Val para evaluar una configuración (CR-020 §C.3.2): solo si el inicio de su
        evaluación consta de forma duradera en el registro (relectura). Si no consta, o el
        registro falta o es ilegible, no se entregan datos y se anota el rechazo."""
        reason = None
        if self.registry is None:
            reason = "sin registro de experimentos"
        elif not Path(self.registry.path).is_file():
            reason = "registro de experimentos ausente"
        else:
            try:                                    # evidencia validada, no un escaneo del archivo (A2)
                pairs = self.registry.accounting()["pairs"]
                if (experiment_id, config_id) not in pairs:
                    reason = f"sin inicio de evaluación registrado para {experiment_id}/{config_id} (CR-020)"
            except Exception as exc:
                reason = f"registro de experimentos ilegible, corrupto o incoherente: {exc!r}"
        if reason:
            self._log("train_val", False, reason, experiment_id)
            raise PartitionAccessError(f"acceso a train_val denegado: {reason}")
        self._log("train_val", True, f"evaluación de la configuración {config_id}", experiment_id)
        df = self._read("train_val")
        return df[df["interval"] == interval].reset_index(drop=True) if interval else df

    def split_train_validation(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        cut = self.manifest["cuts_ms"]["train_end"]
        return (df[df["open_time"] < cut].reset_index(drop=True),
                df[df["open_time"] >= cut].reset_index(drop=True))

    def load_final(self, grant: FinalEvaluationGrant | None, partition: str) -> pd.DataFrame:
        exp = grant.experiment_id if grant else None
        reason = self._deny_reason(grant, partition)
        if reason:
            self._log(partition, False, reason, exp)
            raise PartitionAccessError(f"acceso a {partition} denegado: {reason}")
        claimed = self.registry.claim_partition(
            snapshot_id=self.manifest["snapshot_id"], partition=partition, experiment_id=exp,
            snapshot_last_open_time=self.manifest["range"]["last_open_time_ms"], decision_ref=grant.decision_ref)
        if claimed is None:                                   # otro proceso consumió primero (QA3R2-03)
            reason = f"{partition} ya consumido (evaluación única; consumo concurrente)"
            self._log(partition, False, reason, exp)
            raise PartitionAccessError(f"acceso a {partition} denegado: {reason}")
        self._log(partition, True, f"evaluación final única ({grant.decision_ref})", exp)
        try:
            return self._read(partition)
        except BaseException as exc:
            self._log(partition, False, f"lectura fallida tras el consumo; la partición queda consumida: {exc!r}", exp)
            raise

    def _deny_reason(self, grant: FinalEvaluationGrant | None, partition: str) -> str | None:
        if partition not in SEALED:
            return "partición desconocida"
        if grant is None:
            return "sin autorización de evaluación final"
        if grant.partition != partition or grant.snapshot_id != self.manifest["snapshot_id"]:
            return "la autorización no corresponde a esta partición o snapshot"
        if grant.approved_by != self.owner:
            return "la autorización no es del propietario"
        if self.registry is None:
            return "sin registro de experimentos"
        try:
            enforce_sealing(self.data_dir, self.manifest["files"])   # QA3R2-08: antes del consumo
        except SealingError as exc:
            return f"sellado no efectivo: {exc}"
        why = self.registry.decision_ok(grant.decision_ref, grant.experiment_id, partition, grant.snapshot_id)
        if why:
            return why
        if self.registry.eligible_state(grant.experiment_id) != "OOS_EVALUATION":
            return "el experimento no está en OOS_EVALUATION en el registro (los antecedentes no son elegibles)"
        if self._consumed(partition, grant.experiment_id):
            return f"{partition} ya consumido (evaluación única)"
        return None
