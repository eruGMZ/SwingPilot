"""Registro de experimentos (FEAT-017; REQ-G-104, REQ-G-107, REQ-G-P17; TC-ML-010; DEC-018 decisión 4).

- 12 estados: IDEA → DESIGN → PREREGISTERED → DATA_VALIDATION → DEVELOPMENT → VALIDATION →
  OOS_EVALUATION → AUDIT → HUMAN_REVIEW → APPROVED | REJECTED | INCONCLUSIVE.
- Append-only (JSONL): el estado se obtiene reproduciendo el registro; nada se borra ni se
  reescribe, también los experimentos REJECTED o INCONCLUSIVE (TC-ML-010).
- Ninguna transición a APPROVED (ni la entrada a OOS_EVALUATION, que consume datos de una
  sola evaluación) sin un documento de decisión del propietario existente en docs/decisions.
  La IA no puede aprobar (REQ-G-107).
- Antecedentes declarados por el propietario (EXP-0001, Mean Reversion H1) se registran con
  su origen y cuentan para la corrección por número de experimentos (REQ-G-P17). Solo pueden
  registrarse en PENDING_DOCUMENTATION, REJECTED o INCONCLUSIVE, y no son elegibles para abrir
  particiones ni promover modelos (QA3-03): los consumidores usan `eligible_state()`.
- Identificadores (QA3R2-04): `create()` solo acepta `EXP-NNNN` (cuatro dígitos ASCII, sin
  espacios ni saltos de línea). Los antecedentes declarados conservan el identificador que
  les dio el propietario (p. ej. `ANT-MR-H1`), porque nunca abren particiones ni respaldan
  modelos.
- Decisiones (QA3-04, QA3R2-04): `decision_ref` es un nombre de archivo `DEC-NNN…md` sin ruta,
  dentro de `docs/decisions` del repositorio (el directorio solo se sustituye en pruebas), que
  no sea un enlace simbólico. La autorización no se busca por subcadena en el texto: el
  documento debe contener una línea estructurada, sola en su línea y al inicio de ella, que
  coincida exactamente con lo que se autoriza:
      AUTORIZA: EXP-NNNN                        (transiciones que decide el propietario)
      AUTORIZA: EXP-NNNN <oos|lockbox> SNAP-…   (evaluación final de una partición)
  Cada campo se compara por igualdad exacta (mayúsculas incluidas). Una línea que no siga la
  gramática no autoriza nada. Es un control en proceso, no criptográfico: no autentica a una
  persona; deja la autorización trazable a un documento versionado.
- Consumo de OOS/LOCKBOX (QA3-06): se registra aquí (archivo versionado), no solo en el
  registro de accesos.
- Concurrencia (QA3R2-03): toda escritura toma un `flock` exclusivo sobre `<registro>.lock`;
  `claim_partition` comprueba y anota el consumo dentro del mismo bloqueo, de modo que dos
  procesos no pueden consumir a la vez la misma partición. Requiere un sistema POSIX (Linux,
  como los equipos del proyecto) y un sistema de archivos local.
"""
import contextlib
import fcntl
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .snapshot import SEALED, SNAPSHOT_ID

REPO_DECISIONS_DIR = Path(__file__).resolve().parents[3] / "docs" / "decisions"
_DECISION_NAME = re.compile(r"DEC-[0-9]{3}[A-Za-z0-9_.-]*\.md")            # siempre con fullmatch
EXPERIMENT_ID = re.compile(r"EXP-[0-9]{4}")                                # siempre con fullmatch
_AUTHORIZATION = re.compile(r"AUTORIZA: (EXP-[0-9]{4})(?: (\S+) (\S+))?")  # siempre con fullmatch


def valid_experiment_id(experiment_id) -> bool:
    return isinstance(experiment_id, str) and EXPERIMENT_ID.fullmatch(experiment_id) is not None


def _valid_snapshot_id(snapshot_id) -> bool:
    return isinstance(snapshot_id, str) and SNAPSHOT_ID.fullmatch(snapshot_id) is not None


def authorizations(text: str) -> set[tuple[str, str | None, str | None]]:
    """Líneas «AUTORIZA: …» del documento como tuplas (experimento, partición, snapshot)."""
    out = set()
    for line in text.splitlines():
        m = _AUTHORIZATION.fullmatch(line.rstrip())
        if m:
            out.add(m.groups())
    return out

STATES = ("IDEA", "DESIGN", "PREREGISTERED", "DATA_VALIDATION", "DEVELOPMENT", "VALIDATION",
          "OOS_EVALUATION", "AUDIT", "HUMAN_REVIEW", "APPROVED", "REJECTED", "INCONCLUSIVE")
TERMINAL = ("APPROVED", "REJECTED", "INCONCLUSIVE")
_FORWARD = {
    "IDEA": "DESIGN", "DESIGN": "PREREGISTERED", "PREREGISTERED": "DATA_VALIDATION",
    "DATA_VALIDATION": "DEVELOPMENT", "DEVELOPMENT": "VALIDATION", "VALIDATION": "OOS_EVALUATION",
    "OOS_EVALUATION": "AUDIT", "AUDIT": "HUMAN_REVIEW",
}
# Requisitos verificables por transición (evidencias que deben acompañarla)
_REQUIRES = {
    "PREREGISTERED": ("preregistration_sha256", "min_history_ok"),
    "DEVELOPMENT": ("snapshot_verified",),
    "OOS_EVALUATION": ("decision_ref",),
    "APPROVED": ("decision_ref",),
}
OWNER = "propietario"
DECLARED_ANTECEDENT = "DECLARED_ANTECEDENT"
REGISTRY_ORIGIN = "REGISTRY"
ANTECEDENT_STATES = ("PENDING_DOCUMENTATION", "REJECTED", "INCONCLUSIVE")


class ExperimentError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ExperimentRegistry:
    def __init__(self, path: Path, decisions_dir: Path | None = None, now=_now):
        self.path = Path(path)
        self.decisions_dir = Path(decisions_dir) if decisions_dir is not None else REPO_DECISIONS_DIR
        self._now = now

    # --- lectura ---------------------------------------------------------------------------
    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def experiments(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for r in self.records():
            if r["kind"] in ("CREATED", "ANTECEDENT"):
                out[r["experiment_id"]] = {"experiment_id": r["experiment_id"], "title": r["title"],
                                           "origin": r.get("origin", REGISTRY_ORIGIN), "state": r["state"],
                                           "history": [r]}
            elif r["kind"] == "TRANSITION":
                e = out[r["experiment_id"]]
                e["state"] = r.get("to", e["state"])
                e["history"].append(r)
        return out

    def state(self, experiment_id: str) -> str | None:
        e = self.experiments().get(experiment_id)
        return e["state"] if e else None

    def eligible_state(self, experiment_id: str) -> str | None:
        """Estado solo para experimentos del propio registro; None para antecedentes (QA3-03)."""
        e = self.experiments().get(experiment_id)
        return e["state"] if e and e["origin"] == REGISTRY_ORIGIN else None

    def consumed_partitions(self) -> list[dict]:
        return [r for r in self.records() if r["kind"] == "PARTITION_CONSUMED"]

    def consumed_lockboxes(self) -> list[dict]:
        return [{"snapshot_id": r["snapshot_id"], "snapshot_last_open_time": r["snapshot_last_open_time"]}
                for r in self.consumed_partitions() if r["partition"] == "lockbox"]

    def is_consumed(self, snapshot_id: str, partition: str, experiment_id: str) -> bool:
        for r in self.consumed_partitions():
            if r["snapshot_id"] == snapshot_id and r["partition"] == partition:
                if partition == "lockbox" or r["experiment_id"] == experiment_id:
                    return True
        return False

    def claim_partition(self, *, snapshot_id: str, partition: str, experiment_id: str,
                        snapshot_last_open_time: int, decision_ref: str) -> dict | None:
        """Comprueba y registra el consumo de forma atómica entre procesos (QA3R2-03).
        Devuelve el registro, o None si la partición ya estaba consumida."""
        if not valid_experiment_id(experiment_id):
            raise ExperimentError(f"experimento no válido: {experiment_id!r} (formato EXP-NNNN)")
        if partition not in SEALED:
            raise ExperimentError(f"partición no válida: {partition!r}")
        if not _valid_snapshot_id(snapshot_id):
            raise ExperimentError(f"snapshot no válida: {snapshot_id!r}")
        with self._locked():
            if self.is_consumed(snapshot_id, partition, experiment_id):
                return None
            return self._write({"kind": "PARTITION_CONSUMED", "snapshot_id": snapshot_id, "partition": partition,
                                "experiment_id": experiment_id, "snapshot_last_open_time": snapshot_last_open_time,
                                "decision_ref": decision_ref, "actor": OWNER})

    def record_partition_consumed(self, **kw) -> dict:
        rec = self.claim_partition(**kw)
        if rec is None:
            raise ExperimentError(f"{kw['partition']} de {kw['snapshot_id']} ya consumido (evaluación única)")
        return rec

    def trials_count(self) -> int:
        """Experimentos probados, incluidos antecedentes y rechazados (REQ-G-P17; DEC-018 decisión 4)."""
        return len(self.experiments())

    # --- escritura (append-only) -----------------------------------------------------------
    @contextlib.contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_name(self.path.name + ".lock"), "a") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lk, fcntl.LOCK_UN)

    def _write(self, rec: dict) -> dict:
        """Escribe un registro; el llamador debe tener el bloqueo (`_locked`)."""
        rec = {"at_utc": self._now(), **rec}
        with open(self.path, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return rec

    def _append(self, rec: dict) -> dict:
        with self._locked():
            return self._write(rec)

    def create(self, experiment_id: str, title: str, actor: str) -> dict:
        if not valid_experiment_id(experiment_id):
            raise ExperimentError(f"identificador no válido: {experiment_id!r} (formato EXP-NNNN)")
        if experiment_id in self.experiments():
            raise ExperimentError(f"{experiment_id} ya existe: los IDs no se reutilizan")
        return self._append({"kind": "CREATED", "experiment_id": experiment_id, "title": title,
                             "state": "IDEA", "actor": actor})

    def register_antecedent(self, experiment_id: str, title: str, state: str, source: str, note: str) -> dict:
        """Antecedente declarado por el propietario fuera del registro (p. ej. EXP-0001)."""
        if experiment_id in self.experiments():
            raise ExperimentError(f"{experiment_id} ya existe")
        if state not in ANTECEDENT_STATES:
            raise ExperimentError(f"estado de antecedente no permitido: {state} (solo {ANTECEDENT_STATES})")
        return self._append({"kind": "ANTECEDENT", "experiment_id": experiment_id, "title": title,
                             "state": state, "origin": DECLARED_ANTECEDENT, "source": source,
                             "note": note, "actor": OWNER})

    def decision_ok(self, ref: str | None, experiment_id: str, partition: str | None = None,
                    snapshot_id: str | None = None) -> str | None:
        """None si la decisión autoriza exactamente lo pedido; si no, el motivo (QA3-04, QA3R2-04).
        Sin partición ni snapshot exige `AUTORIZA: <exp>`; con ellas, `AUTORIZA: <exp> <partición> <snapshot>`."""
        if not valid_experiment_id(experiment_id):
            return f"experimento no válido: {experiment_id!r} (formato EXP-NNNN)"
        if (partition is None) != (snapshot_id is None):
            return "la autorización de partición exige partición y snapshot"
        if partition is not None:
            if partition not in SEALED:
                return f"partición no válida: {partition!r}"
            if not _valid_snapshot_id(snapshot_id):
                return f"snapshot no válida: {snapshot_id!r}"
        if not isinstance(ref, str) or not _DECISION_NAME.fullmatch(ref):
            return "decision_ref debe ser un nombre DEC-NNN…md sin ruta"
        path = self.decisions_dir / ref
        if path.is_symlink() or not path.is_file():
            return "la decisión citada no existe en docs/decisions"
        if path.resolve().parent != self.decisions_dir.resolve():
            return "la decisión está fuera de docs/decisions"
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return f"la decisión no se puede leer: {exc!r}"
        wanted = (experiment_id, partition, snapshot_id)
        if wanted not in authorizations(text):
            line = " ".join(x for x in wanted if x is not None)
            return f"la decisión no cita exactamente la línea «AUTORIZA: {line}»"
        return None

    def transition(self, experiment_id: str, to: str, *, actor: str, evidence: dict | None = None,
                   reason: str = "") -> dict:
        evidence = evidence or {}
        exps = self.experiments()
        if experiment_id not in exps:
            raise ExperimentError(f"{experiment_id} no existe")
        e = exps[experiment_id]
        if e["origin"] == DECLARED_ANTECEDENT:
            raise ExperimentError("un antecedente declarado no avanza en el registro")
        cur = e["state"]
        if cur in TERMINAL:
            raise ExperimentError(f"{experiment_id} está en {cur} (terminal)")
        if to not in STATES:
            raise ExperimentError(f"estado desconocido: {to}")
        allowed = {_FORWARD.get(cur)} | {"REJECTED", "INCONCLUSIVE"}
        if cur == "HUMAN_REVIEW":
            allowed |= {"APPROVED"}
        if to not in allowed:
            raise ExperimentError(f"transición no permitida: {cur} → {to}")
        for key in _REQUIRES.get(to, ()):
            if not evidence.get(key):
                raise ExperimentError(f"{cur} → {to} exige la evidencia «{key}»")
        if to == "PREREGISTERED" and evidence.get("min_history_ok") is not True:
            raise ExperimentError("histórico insuficiente: el experimento no pasa de DESIGN (TC-ML-014)")
        if to in ("APPROVED", "OOS_EVALUATION") or (cur == "HUMAN_REVIEW" and to in TERMINAL):
            if actor != OWNER:
                raise ExperimentError(f"{to} solo lo decide el propietario (REQ-G-107)")
            why = self.decision_ok(evidence.get("decision_ref"), experiment_id)
            if why:
                raise ExperimentError(why)
        return self._append({"kind": "TRANSITION", "experiment_id": experiment_id, "from": cur, "to": to,
                             "actor": actor, "evidence": evidence, "reason": reason})
