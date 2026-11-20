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
- Decisiones (QA3-04): `decision_ref` es un nombre de archivo `DEC-NNN…md` sin ruta, dentro de
  `docs/decisions` del repositorio (el directorio solo se sustituye en pruebas), que no sea un
  enlace simbólico y cuyo texto cite los identificadores exigidos (el experimento y, para
  particiones, la partición y la snapshot). Es un control en proceso, no criptográfico: no
  autentica a una persona; deja la autorización trazable a un documento versionado.
- Consumo de OOS/LOCKBOX (QA3-06): se registra aquí (archivo versionado), no solo en el
  registro de accesos.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO_DECISIONS_DIR = Path(__file__).resolve().parents[3] / "docs" / "decisions"
_DECISION_NAME = re.compile(r"^DEC-\d{3}[A-Za-z0-9_.-]*\.md$")

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

    def record_partition_consumed(self, *, snapshot_id: str, partition: str, experiment_id: str,
                                  snapshot_last_open_time: int, decision_ref: str) -> dict:
        return self._append({"kind": "PARTITION_CONSUMED", "snapshot_id": snapshot_id, "partition": partition,
                             "experiment_id": experiment_id, "snapshot_last_open_time": snapshot_last_open_time,
                             "decision_ref": decision_ref, "actor": OWNER})

    def trials_count(self) -> int:
        """Experimentos probados, incluidos antecedentes y rechazados (REQ-G-P17; DEC-018 decisión 4)."""
        return len(self.experiments())

    # --- escritura (append-only) -----------------------------------------------------------
    def _append(self, rec: dict) -> dict:
        rec = {"at_utc": self._now(), **rec}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        return rec

    def create(self, experiment_id: str, title: str, actor: str) -> dict:
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

    def decision_ok(self, ref: str | None, must_cite: list[str]) -> str | None:
        """None si la decisión es válida; si no, el motivo (QA3-04)."""
        if not ref or not _DECISION_NAME.match(ref):
            return "decision_ref debe ser un nombre DEC-NNN…md sin ruta"
        path = self.decisions_dir / ref
        if path.is_symlink() or not path.is_file():
            return "la decisión citada no existe en docs/decisions"
        if path.resolve().parent != self.decisions_dir.resolve():
            return "la decisión está fuera de docs/decisions"
        text = path.read_text(encoding="utf-8", errors="replace")
        missing = [x for x in must_cite if x not in text]
        if missing:
            return f"la decisión no cita {missing}"
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
            why = self.decision_ok(evidence.get("decision_ref"), [experiment_id])
            if why:
                raise ExperimentError(why)
        return self._append({"kind": "TRANSITION", "experiment_id": experiment_id, "from": cur, "to": to,
                             "actor": actor, "evidence": evidence, "reason": reason})
