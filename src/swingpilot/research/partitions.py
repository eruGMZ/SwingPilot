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
- CR-023 (bloque B2): los cargadores son sensibles a `kind`. Los de desarrollo
  (`load_train_val_for_configuration`, `_load_train_val_for_inspection`,
  `split_train_validation`) rechazan una snapshot `evaluation` con PartitionAccessError,
  anotado y sin leer datos. `load_final` deniega (partición no presente) sobre una snapshot
  `development`; sobre una `evaluation` conserva el mecanismo vigente (autorización,
  OOS_EVALUATION, re-comprobación del sellado, consumo atómico y registro sin campos nuevos) y
  exige que la partición pedida y el experimento coincidan con el `window_id` del manifiesto.
  NO implementados aquí (B6): la lectura del `context` junto con su partición, la regla
  OOS-antes-que-LOCKBOX y las comprobaciones V.
- CR-023 (bloque B3, §C.3.3): `load_train_val_for_configuration` exige además el almacén de
  preregistros (`prereg_store`). Lee la clase de independencia de la transición PREREGISTERED y
  verifica el contenido citado en el almacén (hash, experimento y clase coherentes con
  `independence_boundary`); sin almacén, con un fallo de verificación, con contenido de otro
  experimento o con una clase desconocida deniega, anota y no lee datos. El piloto de tasa
  (TRADE_RATE_PILOT) solo recibe la porción Train (`open_time` < `cuts_ms.train_end`): nunca
  Validation. La clase CONFIRMATORY conserva el comportamiento vigente.
- DEC-018: en IMPL-3 no se evalúan OOS ni LOCKBOX; ninguna autorización real se emite.
- CR-020 (§C.3.2) y A2 (opción B del propietario): `load_train_val_for_configuration` solo
  entrega Train+Val si el par (experimento, configuración) está en la evidencia VALIDADA del
  registro (`accounting()["pairs"]`). Registro ausente, ilegible, corrupto, mal formado o
  incoherente → denegado, anotado y sin leer datos (Fail-Closed). QA-CR020-01: si la configuración
  no estaba planificada en la congelación, exige además su DEVIATION obligatoria validada
  (`preregistration.evaluation_evidence_error`); con persistencia parcial (evaluación escrita,
  DEVIATION ausente) el par cuenta pero los datos se deniegan hasta conciliar. La lectura sin configuración
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

from . import boundary as B
from .experiments import REGISTRY_ORIGIN
from .preregistration import evaluation_evidence_error
from .prereg_store import PreregStoreError
from .snapshot import (KIND_DEVELOPMENT, KIND_EVALUATION, MODE_SEALED, SEALED, SEALED_FILES, SealingError,
                       enforce_sealing, load_manifest, sha256_file)


# B2-01 (revisión del propietario, 2026-11-25): restricción temporal Fail-Closed. Una snapshot de
# evaluación sintética con esquema 2.0.0 y el mecanismo de autorización vigente bastarían para
# que `load_final` registrara PARTITION_CONSUMED y leyera la partición sin las comprobaciones de
# CR-023 previstas para B6 (elegibilidad V1–V8, consumo por ventana, OOS antes que LOCKBOX,
# context). Hasta B6 se deniega siempre, después de las comprobaciones vigentes y antes de
# `claim_partition`. No es configurable en ejecución; solo las pruebas del mecanismo histórico
# la desactivan. B6 debe sustituirla por las comprobaciones reales y retirarla.
_FINAL_ACCESS_BLOCKED_UNTIL_B6 = True


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
    prereg_store = None        # CR-023 §C.3.3: sin almacén, el cargador de desarrollo deniega (Fail-Closed)

    def __init__(self, manifest_path: Path, data_root: Path, access_log: Path, *, registry=None,
                 owner: str = "propietario", prereg_store=None):
        self.prereg_store = prereg_store
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
        sealed = partition in SEALED_FILES
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

    def _require_development(self, experiment_id: str | None) -> None:
        """Los cargadores de desarrollo solo aceptan `kind: development` (CR-023 §C.6.5): una
        snapshot de evaluación, o un manifiesto sin `kind`, se rechaza, se anota y no se lee
        (Fail-Closed)."""
        kind = self.manifest.get("kind")
        if kind != KIND_DEVELOPMENT:
            reason = f"el cargador de desarrollo rechaza snapshots kind={kind!r} (CR-023)"
            self._log("train_val", False, reason, experiment_id)
            raise PartitionAccessError(f"acceso a train_val denegado: {reason}")

    def _load_train_val_for_inspection(self, interval: str | None = None) -> pd.DataFrame:
        """Uso interno: inspección de la integridad de la snapshot (FEAT-015). No es una vía de
        evaluación; las evaluaciones usan `load_train_val_for_configuration` (CR-020, A2)."""
        self._require_development(None)
        self._log("train_val", True, "desarrollo", None)
        df = self._read("train_val")
        return df[df["interval"] == interval].reset_index(drop=True) if interval else df

    def load_train_val_for_configuration(self, experiment_id: str, config_id: str,
                                         interval: str | None = None) -> pd.DataFrame:
        """Train+Val para evaluar una configuración (CR-020 §C.3.2): solo si el inicio de su
        evaluación consta de forma duradera en el registro (relectura). Si no consta, o el
        registro falta o es ilegible, no se entregan datos y se anota el rechazo."""
        self._require_development(experiment_id)
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
                else:                               # QA-CR020-01: no planificada → DEVIATION validada
                    reason = evaluation_evidence_error(self.registry, experiment_id, config_id)
            except Exception as exc:
                reason = f"registro de experimentos ilegible, corrupto o incoherente: {exc!r}"
        independence = None
        if not reason:                              # CR-023 §C.3.3: clase de independencia del preregistro
            reason, independence = self._independence_scope(experiment_id)
        train_end = None
        if not reason and independence == B.TRADE_RATE_PILOT:
            train_end = (self.manifest.get("cuts_ms") or {}).get("train_end")
            if not isinstance(train_end, int) or isinstance(train_end, bool):
                reason = "manifiesto sin cuts_ms.train_end: no se puede limitar el piloto de tasa a Train"
        if reason:
            self._log("train_val", False, reason, experiment_id)
            raise PartitionAccessError(f"acceso a train_val denegado: {reason}")
        self._log("train_val", True, f"evaluación de la configuración {config_id}"
                  + (" (piloto de tasa: solo Train)" if train_end is not None else ""), experiment_id)
        df = self._read("train_val")
        if train_end is not None:                   # el piloto nunca recibe Validation
            df = df[df["open_time"] < train_end]
        return df[df["interval"] == interval].reset_index(drop=True) if interval else df.reset_index(drop=True)

    def _independence_scope(self, experiment_id: str) -> tuple[str | None, str | None]:
        """(motivo, clase). Lee la clase de la transición PREREGISTERED del registro y verifica en el
        almacén el contenido citado; la clase debe coincidir con `independence_boundary` del contenido.
        Cualquier fallo o clase desconocida → motivo (denegado). No lee datos de la snapshot."""
        if self.prereg_store is None:
            return "sin almacén de preregistros (CR-023 §C.3.3)", None
        try:
            exp = self.registry.experiments().get(experiment_id)
            if exp is None or exp.get("origin") != REGISTRY_ORIGIN:
                return f"{experiment_id} no es un experimento nativo registrado", None
            pre = [h for h in exp["history"] if h.get("kind") == "TRANSITION" and h.get("to") == "PREREGISTERED"]
            if len(pre) != 1:
                return f"{experiment_id}: sin una única transición a PREREGISTERED", None
            ev = pre[0].get("evidence") or {}
            content = self.prereg_store.verify_cited(experiment_id, ev.get("preregistration_sha256"))
        except PreregStoreError as exc:
            return f"contenido del preregistro no verificable en el almacén: {exc}", None
        except Exception as exc:
            return f"registro o almacén ilegible, corrupto o incoherente: {exc!r}", None
        cls = ev.get("independence_class")
        if cls not in (B.CONFIRMATORY, B.TRADE_RATE_PILOT):
            return f"clase de independencia no válida o ausente: {cls!r}", None
        if content.get("experiment_id") != experiment_id or B.boundary_class(content.get("independence_boundary")) != cls:
            return "el contenido almacenado no corresponde a la clase de independencia congelada", None
        return None, cls

    def split_train_validation(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Train = primeros 5/7 y Validation = últimos 2/7 por fecha (corte del manifiesto)."""
        self._require_development(None)
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
        if self.manifest.get("kind") == KIND_DEVELOPMENT:
            return f"la partición {partition} no existe en una snapshot de desarrollo (kind: development)"
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
        try:                                  # CR-021 §F.2 P1: registro corrupto → denegado y anotado
            if self.registry.eligible_state(grant.experiment_id) != "OOS_EVALUATION":
                return "el experimento no está en OOS_EVALUATION en el registro (los antecedentes no son elegibles)"
            if self._consumed(partition, grant.experiment_id):
                return f"{partition} ya consumido (evaluación única)"
        except Exception as exc:
            return f"registro de experimentos ilegible, corrupto o incoherente: {exc!r}"
        if self.manifest.get("kind") != KIND_EVALUATION:                  # Fail-Closed: sin kind válido
            return "el manifiesto no es de una snapshot de evaluación (kind)"
        wid = self.manifest.get("window_id")
        if wid != f"{grant.experiment_id}/{partition.upper()}":
            return f"la partición pedida no coincide con la ventana del manifiesto ({wid!r})"
        if partition not in self.manifest.get("files", {}):
            return f"la partición {partition} no consta en el manifiesto"
        if _FINAL_ACCESS_BLOCKED_UNTIL_B6:            # B2-01: antes del consumo y de toda lectura
            return ("evaluación final bloqueada hasta B6: faltan las comprobaciones de elegibilidad y de "
                    "consumo por ventana de CR-023 (§C.6.4, §C.9)")
        return None
